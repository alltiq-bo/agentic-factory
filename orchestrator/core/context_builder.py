"""
ContextBuilder — decides what information each agent receives.

Combines:
  1. Role instructions  (what the agent must produce)
  2. Profile knowledge  (domain expertise — loaded from profiles/*.md)
  3. Relevant artifacts (filtered subset of task_artifacts for this step)
  4. Project knowledge  (permanent KB: ADRs, standards, decisions)

The agent base class receives a pre-built list[Message] and never
accesses the full TaskContext directly.
"""
from __future__ import annotations
import logging
from typing import Any

from orchestrator.llm.base import Message, MessageRole
from orchestrator.core.models import AgentDefinition, TaskContext, WorkflowStep
from orchestrator.core.profile_loader import load_profile

logger = logging.getLogger(__name__)

# Maximum characters of artifact content sent per agent call.
# Prevents exceeding model context limits.
MAX_ARTIFACT_CHARS = 12_000


def build(
    agent_def: AgentDefinition,
    step: WorkflowStep,
    context: TaskContext,
    role_instructions: str,
    qa_cycle: int = 0,
) -> list[Message]:
    """
    Assemble the message list for an agent LLM call.

    Parameters
    ----------
    agent_def        : AgentDefinition — role + profile + llm config
    step             : WorkflowStep   — current step (used to filter context_keys)
    context          : TaskContext    — runtime context
    role_instructions: str            — base instructions for this role
    qa_cycle         : int            — current QA cycle number (0 = first pass)
    """
    profile_content = load_profile(agent_def.profile)
    artifacts_block = _select_artifacts(step, context)
    project_block   = _format_project_knowledge(context.project_knowledge)
    cycle_note      = f"\n\n> **QA Fix Cycle {qa_cycle}** — review QA feedback before proceeding." if qa_cycle > 0 else ""

    system = f"""{role_instructions}

## Your Specialization Profile
{profile_content}
"""

    user = f"""## Task
{context.input}{cycle_note}

## Project Knowledge
{project_block}

## Available Artifacts
{artifacts_block}
"""

    return [
        Message(role=MessageRole.SYSTEM, content=system.strip()),
        Message(role=MessageRole.USER,   content=user.strip()),
    ]


def _select_artifacts(step: WorkflowStep, context: TaskContext) -> str:
    """
    Return only the artifacts this step needs.

    If step.context_keys is defined, use that list.
    Otherwise include all artifacts produced so far (bounded by MAX_ARTIFACT_CHARS).
    """
    artifacts = context.task_artifacts
    if not artifacts:
        return "_No artifacts available yet._"

    keys = step.context_keys if step.context_keys else list(artifacts.keys())
    selected: dict[str, Any] = {k: artifacts[k] for k in keys if k in artifacts}

    if not selected:
        return "_No relevant artifacts for this step._"

    lines: list[str] = []
    total = 0
    for key, value in selected.items():
        text = str(value)
        if total + len(text) > MAX_ARTIFACT_CHARS:
            text = text[: MAX_ARTIFACT_CHARS - total] + "\n... [truncated]"
            lines.append(f"### {key}\n{text}")
            break
        lines.append(f"### {key}\n{text}")
        total += len(text)

    return "\n\n".join(lines)


def _format_project_knowledge(knowledge: dict[str, Any]) -> str:
    if not knowledge:
        return "_No project knowledge loaded._"
    lines = [f"### {k}\n{v}" for k, v in knowledge.items()]
    return "\n\n".join(lines)
