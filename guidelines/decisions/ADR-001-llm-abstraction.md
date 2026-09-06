# ADR-001: LLM Provider Abstraction via Adapter Pattern

**Status:** Accepted  
**Date:** 2026-09-06

## Contexto
La plataforma debe soportar múltiples proveedores LLM (Anthropic, OpenAI, Ollama, Gemini)
sin que los agentes dependan de SDKs específicos. Los proyectos que usen esta plataforma
deben poder cambiar de proveedor editando solo configuración YAML.

## Decisión
Implementar el patrón Adapter con:
- `LLMProvider` como clase abstracta (contrato)
- Un adapter por proveedor, registrado via decorador `@register`
- `factory.build(config)` como único punto de instanciación
- Cada agente recibe un `LLMProvider` ya construido — no conoce el proveedor

## Alternativas consideradas
1. **Litellm** — librería que unifica APIs. Descartada: agrega dependencia externa,
   oculta el control del retry/streaming, introduce deuda de actualización.
2. **If/else por proveedor en cada agente** — descartado: viola SRP y hace los agentes
   dependientes del proveedor.

## Consecuencias
- ✅ Cambio de proveedor = editar YAML, no código
- ✅ Nuevo proveedor = agregar un archivo, no modificar existentes
- ✅ Tests pueden usar un proveedor mock sin cambiar agentes
- ⚠️ Cada adapter debe mantenerse sincronizado con el SDK del proveedor
