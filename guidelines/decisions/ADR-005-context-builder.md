# ADR-005: ContextBuilder como componente explícito

**Status:** Accepted
**Date:** 2026-09-06

## Contexto
El primer BaseAgent construía su propio contexto (`_build_messages`, `_read_kb_summary`),
volcando todos los artefactos disponibles al LLM. Eso desperdicia tokens, diluye la
atención del modelo y acopla al agente con la estructura del KB.

## Decisión
`ContextBuilder` es un componente separado, invocado por el Orchestrator antes de
ejecutar cada agente. Recibe `AgentDefinition + WorkflowStep + TaskContext` y produce
`list[Message]` listo para el LLM. El agente base recibe solo los mensajes — no el contexto.

La selección de artefactos se controla por `context_keys` en el workflow YAML:
```yaml
- name: implement_backend
  context_keys: [user_stories, api_contracts, data_model, qa_issues]
```

## Consecuencias
- ✅ Cada agente recibe exactamente lo que necesita — sin ruido
- ✅ El agente base es testeable con cualquier lista de mensajes sin dependencias externas
- ✅ El límite de contexto del modelo es controlable (MAX_ARTIFACT_CHARS)
- ⚠️ `context_keys` vacío = el agente recibe todos los artefactos (fallback seguro pero costoso)
