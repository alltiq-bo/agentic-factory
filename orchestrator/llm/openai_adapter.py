"""OpenAI (GPT) adapter."""
import os
from typing import AsyncIterator
from openai import AsyncOpenAI

from .base import LLMConfig, LLMProvider, LLMResponse, Message
from .factory import register


@register("openai")
class OpenAIProvider(LLMProvider):

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client = AsyncOpenAI(
            api_key=os.environ.get("OPENAI_API_KEY")
        )

    def _to_sdk_messages(self, messages: list[Message]) -> list[dict]:
        return [{"role": m.role.value, "content": m.content} for m in messages]

    async def complete(self, messages: list[Message]) -> LLMResponse:
        response = await self._client.chat.completions.create(
            model=self.config.model,
            messages=self._to_sdk_messages(messages),
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            **self.config.extra,
        )
        choice = response.choices[0]
        return LLMResponse(
            content=choice.message.content,
            provider="openai",
            model=self.config.model,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            raw=response.model_dump(),
        )

    async def stream(self, messages: list[Message]) -> AsyncIterator[str]:
        stream = await self._client.chat.completions.create(
            model=self.config.model,
            messages=self._to_sdk_messages(messages),
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            stream=True,
            **self.config.extra,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
