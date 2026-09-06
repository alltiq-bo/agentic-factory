# Guidelines — Agentic Factory

Este directorio contiene los lineamientos del proyecto.
Son **documentos vivos**: el orquestador los actualiza automáticamente
cada vez que un agente toma una decisión o completa un ciclo.

## Estructura

```
guidelines/
├── decisions/      # Architecture Decision Records (ADRs) generados por Architect Agent
├── standards/      # Coding standards y convenciones por tecnología
├── workflows/      # Definiciones y reglas de flujo de trabajo
└── agents/         # Personas, prompts base y reglas de cada agente
```

## Cómo se actualiza

El `GuidelinesWriter` (invocado por el orquestador al final de cada ciclo)
extrae los ADRs del Knowledge Base y los persiste aquí como Markdown.

Esto permite:
- Trazabilidad de decisiones técnicas
- Reutilización en futuros proyectos (el contexto ya está en disco)
- Revisión humana del razonamiento de los agentes
- Entrada para el siguiente ciclo de QA o desarrollo
