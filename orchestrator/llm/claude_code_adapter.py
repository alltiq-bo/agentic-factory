"""
Claude Code CLI adapter.

Usa el CLI `claude -p` en lugar del SDK de Anthropic.
No requiere ANTHROPIC_API_KEY — usa la sesión activa de Claude Code.

Configurar en el team YAML:
  llm:
    provider: claude_code
    model: sonnet          # alias: sonnet | opus | haiku, o nombre completo
    max_tokens: 8192
"""
from __future__ import annotations
import asyncio
import json
import shutil
from typing import AsyncIterator

from .base import LLMConfig, LLMProvider, LLMResponse, Message, MessageRole
from .factory import register


def _build_prompt(messages: list[Message]) -> str:
    """
    Combina system + user messages en un único prompt de texto.
    El CLI no acepta roles separados, así que concatenamos con marcadores.
    """
    parts = []
    for msg in messages:
        if msg.role == MessageRole.SYSTEM:
            parts.append(f"<system>\n{msg.content}\n</system>")
        elif msg.role == MessageRole.USER:
            parts.append(msg.content)
        elif msg.role == MessageRole.ASSISTANT:
            parts.append(f"<assistant>\n{msg.content}\n</assistant>")
    return "\n\n".join(parts)


@register("claude_code")
class ClaudeCodeProvider(LLMProvider):
    """
    Adapter que invoca el CLI `claude -p` como subprocess.
    Reutiliza la sesión autenticada de Claude Code — sin API key.
    """

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        if not shutil.which("claude"):
            raise RuntimeError(
                "claude CLI no encontrado en PATH. "
                "Instalá Claude Code: npm install -g @anthropic-ai/claude-code"
            )

    def _build_cmd(self) -> list[str]:
        cmd = [
            "claude", "-p",
            "--output-format", "json",
            "--no-session-persistence",
        ]
        if self.config.model:
            cmd += ["--model", self.config.model]
        return cmd

    async def complete(self, messages: list[Message]) -> LLMResponse:
        prompt = _build_prompt(messages)
        cmd    = self._build_cmd()

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin  = asyncio.subprocess.PIPE,
            stdout = asyncio.subprocess.PIPE,
            stderr = asyncio.subprocess.PIPE,
        )

        timeout = max(self.config.timeout, 300)  # mínimo 5 min para tareas largas
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=prompt.encode()),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            proc.kill()
            raise RuntimeError(f"claude CLI timeout después de {timeout}s")

        stdout_str = stdout.decode()
        stderr_str = stderr.decode()

        if proc.returncode != 0:
            # El CLI a veces manda el error al stdout como JSON
            detail = stderr_str.strip() or stdout_str.strip() or "sin detalle"
            raise RuntimeError(
                f"claude CLI error (rc={proc.returncode}): {detail[:500]}"
            )

        raw = json.loads(stdout_str)

        # El CLI puede retornar rc=0 pero con is_error=true
        if raw.get("is_error"):
            raise RuntimeError(f"claude CLI is_error: {raw.get('result', '')[:300]}")

        content  = raw.get("result", "")
        usage    = raw.get("usage", {})

        return LLMResponse(
            content       = content,
            provider      = "claude_code",
            model         = self.config.model or "sonnet",
            input_tokens  = usage.get("input_tokens"),
            output_tokens = usage.get("output_tokens"),
            raw           = raw,
        )

    async def stream(self, messages: list[Message]) -> AsyncIterator[str]:
        # claude_code no implementa streaming real — devuelve la respuesta completa
        response = await self.complete(messages)
        yield response.content
