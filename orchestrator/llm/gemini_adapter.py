"""Google Gemini adapter."""
import os
from typing import AsyncIterator
import google.generativeai as genai

from .base import LLMConfig, LLMProvider, LLMResponse, Message, MessageRole
from .factory import register


@register("gemini")
class GeminiProvider(LLMProvider):

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
        self._model = genai.GenerativeModel(self.config.model)

    def _to_gemini_history(self, messages: list[Message]) -> tuple[str, list[dict]]:
        system_parts = []
        history = []
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system_parts.append(msg.content)
            elif msg.role == MessageRole.USER:
                history.append({"role": "user", "parts": [msg.content]})
            elif msg.role == MessageRole.ASSISTANT:
                history.append({"role": "model", "parts": [msg.content]})
        return "\n".join(system_parts), history

    async def complete(self, messages: list[Message]) -> LLMResponse:
        system_instruction, history = self._to_gemini_history(messages)
        model = genai.GenerativeModel(
            self.config.model,
            system_instruction=system_instruction or None,
        )
        last_user = next(
            (m.content for m in reversed(messages) if m.role == MessageRole.USER), ""
        )
        chat = model.start_chat(history=history[:-1] if history else [])
        response = await chat.send_message_async(
            last_user,
            generation_config=genai.GenerationConfig(
                temperature=self.config.temperature,
                max_output_tokens=self.config.max_tokens,
            ),
        )
        return LLMResponse(
            content=response.text,
            provider="gemini",
            model=self.config.model,
            raw={"candidates": str(response.candidates)},
        )

    async def stream(self, messages: list[Message]) -> AsyncIterator[str]:
        system_instruction, history = self._to_gemini_history(messages)
        model = genai.GenerativeModel(
            self.config.model,
            system_instruction=system_instruction or None,
        )
        last_user = next(
            (m.content for m in reversed(messages) if m.role == MessageRole.USER), ""
        )
        chat = model.start_chat(history=history[:-1] if history else [])
        async for chunk in await chat.send_message_async(
            last_user,
            stream=True,
            generation_config=genai.GenerationConfig(
                temperature=self.config.temperature,
                max_output_tokens=self.config.max_tokens,
            ),
        ):
            if chunk.text:
                yield chunk.text
