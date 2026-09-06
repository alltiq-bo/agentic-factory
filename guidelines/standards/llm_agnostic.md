# Lineamiento: LLM-Agnostic Design

## Principio
Ningún agente debe conocer qué proveedor LLM está usando.
El proveedor es una decisión de configuración, no de código.

## Implementación

### Capa de abstracción (`orchestrator/llm/`)
```
LLMProvider (ABC)          ← contrato
├── AnthropicProvider      ← claude-*
├── OpenAIProvider         ← gpt-*
├── OllamaProvider         ← llama3, codestral, mistral, etc.
└── GeminiProvider         ← gemini-*
```

### Registro de proveedores
Los proveedores se registran con el decorador `@register("nombre")`.
Para agregar un nuevo proveedor:
1. Crear `orchestrator/llm/nuevo_adapter.py`
2. Implementar `LLMProvider` (métodos `complete` y `stream`)
3. Decorar la clase con `@register("nuevo")`
4. Importarlo en `factory.py` → `_load_adapters()`

### Configuración por agente
```yaml
agents:
  analyst:
    llm:
      provider: anthropic   # ← cambia aquí sin tocar código
      model: claude-sonnet-4-6
```

## Interfaz requerida

Todo proveedor debe implementar:
```python
async def complete(messages: list[Message]) -> LLMResponse
async def stream(messages: list[Message]) -> AsyncIterator[str]
```

## Variables de entorno por proveedor
| Proveedor | Variable |
|-----------|----------|
| anthropic | `ANTHROPIC_API_KEY` |
| openai | `OPENAI_API_KEY` |
| gemini | `GOOGLE_API_KEY` |
| ollama | `OLLAMA_BASE_URL` (default: `http://ollama:11434`) |
