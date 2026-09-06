"""
Base Agent — all role agents inherit from this.
Handles: LLM interaction, KB read/write, message passing, retry logic.
"""
from __future__ import annotations
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum

from orchestrator.llm import LLMConfig, LLMResponse, Message, MessageRole, build

logger = logging.getLogger(__name__)


class AgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


@dataclass
class TaskContext:
    """Shared context passed between agents during a workflow execution."""
    task_id: str
    project_id: str
    input: str
    artifacts: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    agent_role: str
    status: AgentStatus
    output: str
    artifacts: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    token_usage: Optional[dict] = None


class BaseAgent:
    """
    LLM-agnostic base agent.

    Subclasses define:
    - role: str — the agent's role name
    - system_prompt: str — persona and instructions
    - output_schema: dict — expected keys in artifacts (optional)
    """

    role: str = "base"
    system_prompt: str = "You are a helpful AI agent."
    output_schema: dict = {}

    def __init__(self, llm_config: LLMConfig, kb_client=None, max_retries: int = 2):
        self.llm = build(llm_config)
        self.kb = kb_client
        self.max_retries = max_retries
        self.status = AgentStatus.IDLE
        logger.info("Agent [%s] initialized with provider %s", self.role, self.llm.name)

    def _build_messages(self, context: TaskContext, extra_prompt: str = "") -> list[Message]:
        """Construct the message list for the LLM call."""
        kb_summary = self._read_kb_summary(context)
        user_content = f"""## Task
{context.input}

## Available Context from Knowledge Base
{kb_summary}

{extra_prompt}
"""
        return [
            Message(role=MessageRole.SYSTEM, content=self.system_prompt),
            Message(role=MessageRole.USER, content=user_content.strip()),
        ]

    def _read_kb_summary(self, context: TaskContext) -> str:
        """Read relevant artifacts from KB for this task."""
        if not self.kb or not context.artifacts:
            return "No prior artifacts available."
        lines = []
        for key, value in context.artifacts.items():
            lines.append(f"### {key}\n{value}")
        return "\n\n".join(lines)

    def _parse_output(self, response: LLMResponse, context: TaskContext) -> dict[str, Any]:
        """
        Parse LLM response into structured artifacts.
        Subclasses override this to extract structured data.
        """
        return {"raw_output": response.content}

    async def _write_to_kb(self, context: TaskContext, artifacts: dict[str, Any]) -> None:
        """Persist artifacts to the knowledge base."""
        if self.kb:
            await self.kb.write(
                task_id=context.task_id,
                agent_role=self.role,
                artifacts=artifacts,
            )
        else:
            # Update in-memory context when no KB client available
            context.artifacts.update(artifacts)

    async def run(self, context: TaskContext) -> AgentResult:
        """Execute the agent — call LLM, parse output, write to KB."""
        self.status = AgentStatus.RUNNING
        attempt = 0

        while attempt <= self.max_retries:
            try:
                messages = self._build_messages(context)
                logger.info(
                    "Agent [%s] calling %s (attempt %d)",
                    self.role, self.llm.name, attempt + 1
                )
                response = await self.llm.complete(messages)
                artifacts = self._parse_output(response, context)
                await self._write_to_kb(context, artifacts)

                self.status = AgentStatus.DONE
                return AgentResult(
                    agent_role=self.role,
                    status=AgentStatus.DONE,
                    output=response.content,
                    artifacts=artifacts,
                    token_usage={
                        "input": response.input_tokens,
                        "output": response.output_tokens,
                    },
                )

            except Exception as exc:
                attempt += 1
                logger.warning(
                    "Agent [%s] failed attempt %d: %s",
                    self.role, attempt, exc
                )
                if attempt > self.max_retries:
                    self.status = AgentStatus.FAILED
                    return AgentResult(
                        agent_role=self.role,
                        status=AgentStatus.FAILED,
                        output="",
                        error=str(exc),
                    )
                await asyncio.sleep(2 ** attempt)  # exponential backoff

    async def stream_run(self, context: TaskContext):
        """Stream tokens as they arrive — yields str chunks."""
        messages = self._build_messages(context)
        async for chunk in self.llm.stream(messages):
            yield chunk
