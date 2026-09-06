# Workflow: software_development

## Descripción
Flujo de trabajo estándar para desarrollo de software iterativo con equipo completo de agentes.

## Diagrama de flujo
```
GitHub Issue / Input
        │
        ▼
[1] Analyst (sequential)
    → user_stories, acceptance_criteria
        │
        ▼
[2] Architect (sequential)
    → system_architecture, api_contracts, ADRs
        │
    ┌───┴───┐
    ▼       ▼
[3a] Backend  [3b] Frontend  (parallel)
    └───┬───┘
        ▼
[4] QA (sequential)
    │
    ├── PASS → DONE
    └── FAIL → back to [3] (max_qa_cycles)
```

## Definición de pasos

| Paso | Agente | Modo | Depende de |
|------|--------|------|-----------|
| analyze_requirements | analyst | sequential | — |
| design_architecture | architect | sequential | analyze_requirements |
| implement_backend | backend_dev | parallel | design_architecture |
| implement_frontend | frontend_dev | parallel | design_architecture |
| validate | qa | sequential | implement_backend, implement_frontend |

## Contexto compartido entre pasos
Cada agente lee del KB los artefactos de los pasos anteriores:
- `architect` lee: `user_stories`, `acceptance_criteria`
- `backend_dev` lee: `system_architecture`, `api_contracts`, `data_model`
- `frontend_dev` lee: `system_architecture`, `api_contracts`, `component_tree`
- `qa` lee: todos los artefactos anteriores + output de ambos devs

## Política de reintentos
- Cada agente tiene `retry_max: 2` con backoff exponencial
- Si un agente falla 3 veces → workflow status = `failed` → escalación humana

## Condición de término
- `status: done` → todos los pasos completados con QA PASS
- `status: failed` → agente falló sin recuperación
- `status: max_qa_cycles_exceeded` → QA falló N veces seguidas → escalación
