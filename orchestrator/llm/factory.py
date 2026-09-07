"""
LLM Provider factory — resolves provider name to concrete implementation.
Add new providers here without changing agent code.
"""
from typing import Type
from .base import LLMConfig, LLMProvider


_REGISTRY: dict[str, Type[LLMProvider]] = {}


def register(name: str):
    """Decorator to register a provider by name."""
    def decorator(cls: Type[LLMProvider]):
        _REGISTRY[name] = cls
        return cls
    return decorator


def build(config: LLMConfig) -> LLMProvider:
    """Instantiate the correct provider from config."""
    provider_cls = _REGISTRY.get(config.provider)
    if provider_cls is None:
        available = list(_REGISTRY.keys())
        raise ValueError(
            f"Unknown LLM provider '{config.provider}'. "
            f"Available: {available}"
        )
    return provider_cls(config)


def available_providers() -> list[str]:
    return list(_REGISTRY.keys())


# Auto-import adapters so decorators run and register providers
def _load_adapters():
    from . import anthropic_adapter    # noqa: F401
    from . import claude_code_adapter  # noqa: F401
    from . import openai_adapter       # noqa: F401
    from . import ollama_adapter       # noqa: F401
    from . import gemini_adapter       # noqa: F401


_load_adapters()
