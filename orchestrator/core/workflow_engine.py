"""
Workflow Engine — executes agent workflows defined by YAML config.

Supports:
- Sequential steps
- Parallel steps (fan-out / fan-in)
- Conditional branching (e.g. QA pass/fail)
- Retry policies per step
- Event hooks (on_start, on_complete, on_fail)
"""
from __future__ import annotations
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from enum import Enum

from agents.base.agent import AgentResult, AgentStatus, BaseAgent, TaskContext

logger = logging.getLogger(__name__)


class StepMode(str, Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"


@dataclass
class WorkflowStep:
    name: str
    agent_role: str
    mode: StepMode = StepMode.SEQUENTIAL
    depends_on: list[str] = field(default_factory=list)
    condition: Optional[str] = None        # e.g. "artifacts.qa_status == 'fail'"
    on_fail: Optional[str] = None          # step name to go to on failure
    retry_max: int = 2
    extra_prompt: str = ""


@dataclass
class WorkflowDefinition:
    name: str
    steps: list[WorkflowStep]
    max_qa_cycles: int = 3


@dataclass
class WorkflowRun:
    workflow_name: str
    task_id: str
    results: dict[str, AgentResult] = field(default_factory=dict)
    status: str = "running"
    qa_cycle: int = 0
    error: Optional[str] = None


class WorkflowEngine:
    """
    Executes a WorkflowDefinition against a TaskContext using a registry of agents.

    Usage:
        engine = WorkflowEngine(agents={"analyst": AnalystAgent(...)})
        run = await engine.execute(workflow_def, context)
    """

    def __init__(
        self,
        agents: dict[str, BaseAgent],
        on_step_start: Optional[Callable] = None,
        on_step_complete: Optional[Callable] = None,
        on_step_fail: Optional[Callable] = None,
    ):
        self.agents = agents
        self._on_step_start = on_step_start
        self._on_step_complete = on_step_complete
        self._on_step_fail = on_step_fail

    async def execute(
        self,
        workflow: WorkflowDefinition,
        context: TaskContext,
    ) -> WorkflowRun:
        run = WorkflowRun(workflow_name=workflow.name, task_id=context.task_id)
        completed: set[str] = set()
        pending = list(workflow.steps)

        logger.info("Workflow [%s] started for task %s", workflow.name, context.task_id)

        while pending:
            # Find steps whose dependencies are all met
            ready = [
                s for s in pending
                if all(dep in completed for dep in s.depends_on)
                and self._eval_condition(s.condition, context)
            ]

            if not ready:
                logger.error(
                    "Workflow deadlock — no ready steps. Completed: %s, Pending: %s",
                    completed, [s.name for s in pending]
                )
                run.status = "deadlock"
                break

            # Split into parallel groups and sequential steps
            parallel_steps = [s for s in ready if s.mode == StepMode.PARALLEL]
            sequential_steps = [s for s in ready if s.mode == StepMode.SEQUENTIAL]

            # Execute parallel batch first, then each sequential step
            if parallel_steps:
                results = await self._run_parallel(parallel_steps, context)
                for step, result in zip(parallel_steps, results):
                    run.results[step.name] = result
                    context.artifacts[f"{step.agent_role}_result"] = result.output
                    if result.status == AgentStatus.DONE:
                        completed.add(step.name)
                    else:
                        await self._handle_failure(step, result, run, context)
                pending = [s for s in pending if s not in parallel_steps]

            for step in sequential_steps:
                result = await self._run_step(step, context)
                run.results[step.name] = result
                context.artifacts[f"{step.agent_role}_result"] = result.output

                if result.status == AgentStatus.DONE:
                    completed.add(step.name)
                    # QA cycle check
                    if step.agent_role == "qa":
                        qa_passed = self._check_qa_pass(result)
                        context.artifacts["qa_status"] = "pass" if qa_passed else "fail"
                        if not qa_passed:
                            run.qa_cycle += 1
                            if run.qa_cycle >= workflow.max_qa_cycles:
                                run.status = "max_qa_cycles_exceeded"
                                run.error = f"QA failed after {run.qa_cycle} cycles"
                                return run
                            logger.info(
                                "QA FAIL — starting fix cycle %d/%d",
                                run.qa_cycle, workflow.max_qa_cycles
                            )
                            # Re-queue developer steps
                            dev_steps = [
                                s for s in workflow.steps
                                if s.agent_role in ("backend_dev", "frontend_dev")
                            ]
                            for ds in dev_steps:
                                completed.discard(ds.name)
                            pending.extend(dev_steps)
                            pending = [s for s in pending if s not in [step]]
                            break  # restart loop with new pending
                else:
                    await self._handle_failure(step, result, run, context)

                pending.remove(step)

        if run.status == "running":
            run.status = "done"
            logger.info("Workflow [%s] completed for task %s", workflow.name, context.task_id)

        return run

    async def _run_step(self, step: WorkflowStep, context: TaskContext) -> AgentResult:
        agent = self.agents.get(step.agent_role)
        if not agent:
            raise ValueError(f"No agent registered for role '{step.agent_role}'")

        if self._on_step_start:
            await self._on_step_start(step, context)

        logger.info("Step [%s] starting", step.name)
        result = await agent.run(context)

        if result.status == AgentStatus.DONE and self._on_step_complete:
            await self._on_step_complete(step, result, context)
        elif result.status == AgentStatus.FAILED and self._on_step_fail:
            await self._on_step_fail(step, result, context)

        return result

    async def _run_parallel(
        self, steps: list[WorkflowStep], context: TaskContext
    ) -> list[AgentResult]:
        tasks = [self._run_step(step, context) for step in steps]
        return await asyncio.gather(*tasks, return_exceptions=False)

    async def _handle_failure(
        self,
        step: WorkflowStep,
        result: AgentResult,
        run: WorkflowRun,
        context: TaskContext,
    ) -> None:
        logger.error("Step [%s] failed: %s", step.name, result.error)
        if step.on_fail:
            logger.info("Routing to fallback step: %s", step.on_fail)
            context.artifacts["last_error"] = result.error
        else:
            run.status = "failed"
            run.error = f"Step '{step.name}' failed: {result.error}"

    def _eval_condition(self, condition: Optional[str], context: TaskContext) -> bool:
        if not condition:
            return True
        try:
            return bool(eval(condition, {"artifacts": context.artifacts}))  # noqa: S307
        except Exception:
            return True

    def _check_qa_pass(self, result: AgentResult) -> bool:
        """Determine if QA passed based on agent output artifacts."""
        status = result.artifacts.get("qa_status", "")
        if status:
            return str(status).lower() == "pass"
        # Fallback: look for keywords in raw output
        output_lower = result.output.lower()
        fail_signals = ["fail", "error", "issue", "bug", "defect", "rejected"]
        return not any(sig in output_lower for sig in fail_signals)
