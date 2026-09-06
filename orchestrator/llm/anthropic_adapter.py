"""Anthropic (Claude) adapter."""
import os
from typing import AsyncIterator
import anthropic

from .base import LLMConfig, LLMProvider, LLMResponse, Message, MessageRole
from .factory import register


@register("anthropic")
class AnthropicProvider(LLMProvider):

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client = anthropic.AsyncAnthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY")
        )

    def _to_sdk_messages(self, messages: list[Message]) -> tuple[str | None, list[dict]]:
        system_prompt = None
        sdk_messages = []
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system_prompt = msg.content
            else:
                sdk_messages.append({"role": msg.role.value, "content": msg.content})
        return system_prompt, sdk_messages

    async def complete(self, messages: list[Message]) -> LLMResponse:
        system, msgs = self._to_sdk_messages(messages)
        kwargs = dict(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            messages=msgs,
            **self.config.extra,
        )
        if system:
            kwargs["system"] = system

        response = await self._client.messages.create(**kwargs)
        return LLMResponse(
            content=response.content[0].text,
            provider="anthropic",
            model=self.config.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            raw=response.model_dump(),
        )

    async def stream(self, messages: list[Message]) -> AsyncIterator[str]:
        system, msgs = self._to_sdk_messages(messages)
        kwargs = dict(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            messages=msgs,
            **self.config.extra,
        )
        if system:
            kwargs["system"] = system

        async with self._client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield text
