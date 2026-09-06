# Architecture Diagrams — Agentic Factory

Diagramas modelados en [Mermaid](https://mermaid.js.org/). Se renderizan automáticamente en GitHub, GitLab y Notion.

## Archivos

| Archivo | Descripción |
|---------|-------------|
| `01_workflow_main.mmd` | Flujo principal: GitHub → Orchestrator → Agentes → KB |
| `02_sequence_task.mmd` | Secuencia detallada de ejecución de una tarea |
| `03_deployment_docker.mmd` | Arquitectura de despliegue (contenedores Docker) |
| `04_state_machine.mmd` | Máquina de estados de una tarea |
| `05_knowledge_base.mmd` | Modelo de datos del Knowledge Base |

## Vista rápida

```
GitHub Issue
    │
    ▼
Orchestrator (FastAPI + Router + State)
    │
    ▼
Analyst ──► Architect ──► Backend ─┐
                                    ├──► QA ──► PASS → Done / FAIL → Fix cycle
                         Frontend ─┘
    │
    ▼
Knowledge Base (PostgreSQL + Redis + Vector Store)
```

## Renderizar localmente

```bash
# Con mmdc (Mermaid CLI)
npm install -g @mermaid-js/mermaid-cli
mmdc -i 01_workflow_main.mmd -o 01_workflow_main.svg

# O usar la extensión Mermaid Preview en VS Code
```
