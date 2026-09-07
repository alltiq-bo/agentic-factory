"""
Orchestrator — central coordinator.

Responsibilities:
  1. Receive a task and create its state
  2. Load team configuration (agents + workflow)
  3. Build TaskContext with project knowledge
  4. Execute WorkflowEngine with a runner that:
       - resolves the agent class by role
       - builds messages via ContextBuilder
       - runs the agent
       - persists artifacts to KB
  5. Update StateManager at every transition
  6. After completion: flush profile suggestions from QA artifacts
"""
from __future__ import annotations
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx

from orchestrator.core.models import (
    AgentDefinition, AgentResult, AgentRunStatus,
    TaskContext, TaskState, TaskStatus,
    WorkflowStep, WorkflowRun,
)
from orchestrator.core.config_loader import load_team
from orchestrator.core.context_builder import build as build_context
from orchestrator.core.state_manager import StateManager
from orchestrator.core.workflow_engine import WorkflowEngine
from orchestrator.llm.factory import build as build_llm
from knowledge_base.store import KnowledgeBase

logger = logging.getLogger(__name__)

# ── Agent class registry ───────────────────────────────────────────────────
# Maps role name → agent class. Add new roles here.
from agents.analyst.agent      import AnalystAgent
from agents.architect.agent    import ArchitectAgent
from agents.backend_dev.agent  import BackendDevAgent
from agents.frontend_dev.agent import FrontendDevAgent
from agents.qa.agent           import QAAgent

AGENT_REGISTRY = {
    "analyst":             AnalystAgent,
    "architect":           ArchitectAgent,
    "backend_developer":   BackendDevAgent,
    "frontend_developer":  FrontendDevAgent,
    "qa":                  QAAgent,
}


class Orchestrator:

    def __init__(
        self,
        state_manager: StateManager,
        knowledge_base: KnowledgeBase,
        team_name: str = "dotnet-react-migration",
    ):
        self.sm        = state_manager
        self.kb        = knowledge_base
        self.team_name = team_name
        self._team     = load_team(team_name)

        # Build agent index: role → AgentDefinition
        self._agent_defs: dict[str, AgentDefinition] = {
            a.role: a for a in self._team.agents
        }

    async def run_task(
        self,
        input_text: str,
        project_id: str = "default",
        task_id: Optional[str] = None,
        github_issue: Optional[dict] = None,   # {"repo": "owner/repo", "number": N}
    ) -> WorkflowRun:
        task_id = task_id or str(uuid.uuid4())

        # ── 1. Create task state ───────────────────────────────────────────
        state = await self.sm.create(TaskState(
            task_id       = task_id,
            project_id    = project_id,
            status        = TaskStatus.CREATED,
            workflow_name = self._team.workflow.name,
        ))

        # ── 2. Build TaskContext ───────────────────────────────────────────
        project_knowledge = self.kb.load_project_knowledge(
            sections=["decisions", "standards"]
        )
        context = TaskContext(
            task_id           = task_id,
            project_id        = project_id,
            input             = input_text,
            project_knowledge = project_knowledge,
        )

        # ── 3. Run workflow ────────────────────────────────────────────────
        engine = WorkflowEngine(
            runner            = self._make_runner(context),
            on_step_start     = self._on_step_start,
            on_step_complete  = self._on_step_complete,
            on_step_fail      = self._on_step_fail,
        )

        run = await engine.execute(self._team.workflow, context)

        # ── 4. Final state transition ──────────────────────────────────────
        final_status = {
            "done":      TaskStatus.DONE,
            "failed":    TaskStatus.FAILED,
            "escalated": TaskStatus.ESCALATED,
            "deadlock":  TaskStatus.FAILED,
        }.get(run.status, TaskStatus.FAILED)

        await self.sm.transition(
            task_id,
            final_status,
            error=run.error,
        )

        # ── 5. Flush profile suggestions from QA ──────────────────────────
        await self._flush_profile_suggestions(context, task_id)

        # ── 6. Post comment to GitHub issue if origin was an issue ────────
        if github_issue:
            await self._post_github_comment(github_issue, run)

        return run

    # ── Runner factory (injected into WorkflowEngine) ─────────────────────

    def _make_runner(self, context: TaskContext):
        async def runner(step: WorkflowStep, ctx: TaskContext, qa_cycle: int) -> AgentResult:
            agent_def = self._agent_defs.get(step.agent_role)
            if not agent_def:
                return AgentResult(
                    agent_role = step.agent_role,
                    status     = AgentRunStatus.FAILED,
                    output     = "",
                    error      = f"No agent configured for role '{step.agent_role}'",
                )

            agent_cls = AGENT_REGISTRY.get(step.agent_role)
            if not agent_cls:
                return AgentResult(
                    agent_role = step.agent_role,
                    status     = AgentRunStatus.FAILED,
                    output     = "",
                    error      = f"No agent class registered for role '{step.agent_role}'",
                )

            llm   = build_llm(agent_def.llm)
            agent = agent_cls(llm=llm, max_retries=step.retry_max)

            messages = build_context(
                agent_def         = agent_def,
                step              = step,
                context           = ctx,
                role_instructions = agent.ROLE_INSTRUCTIONS,
                qa_cycle          = qa_cycle,
            )

            result = await agent.run(messages)

            # Persist artifacts to KB
            if result.artifacts:
                await self.kb.write_artifacts(
                    task_id    = ctx.task_id,
                    agent_role = step.agent_role,
                    artifacts  = result.artifacts,
                )

            return result
        return runner

    # ── State hooks ────────────────────────────────────────────────────────

    def _on_step_start(self, step: WorkflowStep, context: TaskContext) -> None:
        status_map = {
            "analyst":            TaskStatus.ANALYZING,
            "architect":          TaskStatus.DESIGNING,
            "backend_developer":  TaskStatus.DEVELOPING,
            "frontend_developer": TaskStatus.DEVELOPING,
            "qa":                 TaskStatus.VALIDATING,
        }
        status = status_map.get(step.agent_role, TaskStatus.DEVELOPING)
        logger.info("▶ Step [%s] — agente: %s", step.name, step.agent_role)
        import asyncio
        asyncio.create_task(
            self.sm.transition(context.task_id, status, current_step=step.name)
        )

    def _on_step_complete(
        self, step: WorkflowStep, result: AgentResult, context: TaskContext
    ) -> None:
        logger.info("✔ Step [%s] OK — role=%s", step.name, step.agent_role)

    def _on_step_fail(
        self, step: WorkflowStep, result: AgentResult, context: TaskContext
    ) -> None:
        logger.error("✘ Step [%s] FAILED — %s", step.name, result.error)

    # ── GitHub comment ────────────────────────────────────────────────────

    async def _post_github_comment(self, github_issue: dict, run: WorkflowRun) -> None:
        repo   = github_issue.get("repo", "")
        number = github_issue.get("number")
        token  = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

        if not repo or not number or not token:
            logger.warning("GitHub comment skipped — missing repo, number or GH_TOKEN")
            return

        # Comentario corto — solo estado y pasos ejecutados
        pasos = ", ".join(run.results.keys()) or "ninguno"
        if run.status == "done":
            body = f"✅ Completado por agentes ({pasos})."
        else:
            body = f"❌ Fallido en `{run.error or 'error desconocido'}` — pasos ejecutados: {pasos}."

        url = f"https://api.github.com/repos/{repo}/issues/{number}/comments"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(url, headers=headers, json={"body": body})
            if resp.status_code == 201:
                logger.info("GitHub comment posted → %s#%s", repo, number)
            else:
                logger.warning("GitHub comment failed: %s %s", resp.status_code, resp.text[:200])
        except Exception as e:
            logger.warning("GitHub comment error: %s", e)

    # ── Profile suggestion flush ───────────────────────────────────────────

    async def _flush_profile_suggestions(
        self, context: TaskContext, task_id: str
    ) -> None:
        suggestions = context.task_artifacts.get("qa_profile_suggestions", [])
        if not suggestions:
            return
        for s in suggestions:
            profile = s.get("profile", "")
            text    = f"**Section:** {s.get('section', '')}\n\n{s.get('suggestion', '')}"
            if profile:
                await self.kb.write_profile_suggestion(profile, text, task_id)
