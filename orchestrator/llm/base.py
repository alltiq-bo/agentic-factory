"""
LLM Provider abstraction — agnostic interface for all language model backends.
Any provider must implement this contract.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional
from enum import Enum


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class Message:
    role: MessageRole
    content: str


@dataclass
class LLMConfig:
    provider: str                          # anthropic | openai | ollama | gemini
    model: str
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 120
    extra: dict = field(default_factory=dict)  # provider-specific params


@dataclass
class LLMResponse:
    content: str
    provider: str
    model: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    raw: Optional[dict] = None


class LLMProvider(ABC):
    """Abstract base — every LLM adapter must implement these methods."""

    def __init__(self, config: LLMConfig):
        self.config = config

    @abstractmethod
    async def complete(self, messages: list[Message]) -> LLMResponse:
        """Send messages and return a complete response."""
        ...

    @abstractmethod
    async def stream(self, messages: list[Message]) -> AsyncIterator[str]:
        """Stream response tokens as they arrive."""
        ...

    @property
    def name(self) -> str:
        return f"{self.config.provider}/{self.config.model}"
