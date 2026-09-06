"""Ollama adapter — local LLM inference (llama3, mistral, codestral, etc.)."""
import os
from typing import AsyncIterator
import httpx

from .base import LLMConfig, LLMProvider, LLMResponse, Message
from .factory import register


@register("ollama")
class OllamaProvider(LLMProvider):

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._base_url = os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434")

    def _to_payload(self, messages: list[Message], stream: bool = False) -> dict:
        return {
            "model": self.config.model,
            "messages": [{"role": m.role.value, "content": m.content} for m in messages],
            "stream": stream,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
                **self.config.extra,
            },
        }

    async def complete(self, messages: list[Message]) -> LLMResponse:
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                f"{self._base_url}/api/chat",
                json=self._to_payload(messages, stream=False),
            )
            response.raise_for_status()
            data = response.json()
            return LLMResponse(
                content=data["message"]["content"],
                provider="ollama",
                model=self.config.model,
                raw=data,
            )

    async def stream(self, messages: list[Message]) -> AsyncIterator[str]:
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/api/chat",
                json=self._to_payload(messages, stream=True),
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        import json
                        chunk = json.loads(line)
                        if content := chunk.get("message", {}).get("content"):
                            yield content
