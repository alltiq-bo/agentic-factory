# ADR-004: Ciclo QA/fix config-driven — WorkflowEngine domain-agnóstico

**Status:** Accepted
**Date:** 2026-09-06

## Contexto
El primer WorkflowEngine tenía hardcodeado: `if step.agent_role == "qa"` y
`if s.agent_role in ("backend_dev", "frontend_dev")`. Eso acopla el engine
al dominio y rompe la reutilización entre equipos con roles distintos.

## Decisión
El engine no conoce ningún nombre de rol. La política de requeue se define en el workflow YAML:
```yaml
on_fail:
  requeue: [implement_backend, implement_frontend]
  max_cycles: 3
```
El engine detecta fallo cuando el agente escribe `<role>_passed: false` en sus artefactos.
Qué steps re-encolar y cuántas veces es decisión del workflow, no del engine.

## Consecuencias
- ✅ El engine es reutilizable sin modificación para cualquier workflow
- ✅ Cambiar quién hace QA o quién hace dev = editar YAML
- ⚠️ La convención `<role>_passed` debe ser respetada por todos los agentes que puedan disparar un requeue
