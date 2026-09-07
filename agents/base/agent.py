"""
Base Agent — LLM caller + output parser.

The agent does NOT build its own context. It receives pre-built messages
from ContextBuilder and returns structured artifacts.

Subclasses define:
  ROLE_INSTRUCTIONS : str  — what the agent must produce (role contract)
  _parse_output()          — extract structured artifacts from LLM response
"""
from __future__ import annotations
import asyncio
import logging
from typing import Any, AsyncIterator

from orchestrator.llm.base import LLMProvider, LLMResponse, Message
from orchestrator.core.models import AgentResult, AgentRunStatus

logger = logging.getLogger(__name__)


class BaseAgent:
    ROLE_INSTRUCTIONS: str = "You are a helpful AI agent."

    def __init__(self, llm: LLMProvider, max_retries: int = 2):
        self.llm         = llm
        self.max_retries = max_retries

    # ── Public interface ──────────────────────────────────────────────────

    async def run(self, messages: list[Message]) -> AgentResult:
        """Execute with pre-built messages. Returns structured AgentResult."""
        attempt = 0
        name    = self.__class__.__name__
        while attempt <= self.max_retries:
            try:
                logger.info("┌─ [%s] iniciando — modelo: %s", name, self.llm.name)
                response  = await self.llm.complete(messages)
                artifacts = self._parse_output(response)

                preview = response.content[:120].replace("\n", " ")
                logger.info("└─ [%s] completado — tokens: %s entrada / %s salida | preview: %s...",
                            name,
                            response.input_tokens or "?",
                            response.output_tokens or "?",
                            preview)

                return AgentResult(
                    agent_role  = self._role_name(),
                    status      = AgentRunStatus.DONE,
                    output      = response.content,
                    artifacts   = artifacts,
                    token_usage = {
                        "input":  response.input_tokens,
                        "output": response.output_tokens,
                    },
                )
            except Exception as exc:
                attempt += 1
                logger.warning("✗ [%s] intento %d/%d fallido: %s",
                               name, attempt, self.max_retries + 1, exc)
                if attempt > self.max_retries:
                    return AgentResult(
                        agent_role = self._role_name(),
                        status     = AgentRunStatus.FAILED,
                        output     = "",
                        error      = str(exc),
                    )
                wait = 2 ** attempt
                logger.info("  reintentando en %ds...", wait)
                await asyncio.sleep(wait)

    async def stream(self, messages: list[Message]) -> AsyncIterator[str]:
        async for chunk in self.llm.stream(messages):
            yield chunk

    # ── Overridable ───────────────────────────────────────────────────────

    def _parse_output(self, response: LLMResponse) -> dict[str, Any]:
        """
        Extract structured artifacts from LLM response.
        Subclasses override to parse sections and set domain-specific keys.
        """
        return {"raw_output": response.content}

    def _role_name(self) -> str:
        return self.__class__.__name__.lower().replace("agent", "")

    # ── Shared section parser ─────────────────────────────────────────────

    @staticmethod
    def _extract_sections(content: str, section_names: list[str]) -> dict[str, str]:
        """Parse ## Section headers into a dict."""
        import re
        result: dict[str, str] = {}
        for section in section_names:
            pattern = rf"## {re.escape(section)}\n(.*?)(?=\n## |\Z)"
            match   = re.search(pattern, content, re.DOTALL)
            if match:
                key = section.lower().replace(" ", "_").replace("-", "_")
                result[key] = match.group(1).strip()
        return result
