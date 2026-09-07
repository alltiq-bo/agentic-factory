# CLAUDE.md — Agentic Factory

Contexto del proyecto para cualquier sesión de Claude Code.

---

## Proyecto

Plataforma reutilizable para orquestar equipos de agentes AI en proyectos de software.
Equipos definidos por YAML — sin modificar código para crear un equipo nuevo.

**Repo:** alltiq-bo/agentic-factory  
**Proyecto target:** vega-bo/web.agro.nt (migración .NET MVC 5 → .NET 9 + React)

---

## Cómo correr

Redis en Docker, orquestador en host (claude_code no funciona dentro de Docker — OAuth ligado a sesión local):

```bash
docker compose up redis -d
source .env && export $(grep -v '^#' .env | xargs)
nohup python3 -m uvicorn orchestrator.api.main:app --host 0.0.0.0 --port 8000 > /tmp/orchestrator.log 2>&1 &
tail -f /tmp/orchestrator.log
```

Lanzar tarea desde GitHub Issue:

```bash
curl -X POST http://localhost:8000/tasks/sync \
  -H "Content-Type: application/json" \
  -d '{"github_issue": {"repo": "vega-bo/web.agro.nt", "number": 12}, "workflow": "analysis_only", "project_id": "web-agro-nt"}'
```

---

## Variables de entorno (.env)

| Variable | Descripción |
|----------|-------------|
| `GH_TOKEN` | Personal Access Token GitHub — scopes: `repo` + `project` |
| `TEAM_CONFIG` | Nombre del team YAML (ej. `dotnet-react-migration`) |
| `CLAUDE_BIN` | Path al binario claude (ej. `/root/.npm-global/bin/claude`) |
| `CLAUDE_CONFIG_DIR` | Sesión Claude a usar (ej. `~/.claude-personal`, `~/.claude-work`) |
| `CLAUDE_ADD_DIRS` | Dirs accesibles por subprocess, separados por `:` |
| `CLAUDE_TIMEOUT` | Timeout en segundos por llamada al CLI (default: 600) |

---

## Decisiones de arquitectura — NO revertir

**WorkflowEngine es domain-agnóstico**  
El engine NO tiene `if step.agent_role == "qa"` ni nombres hardcodeados. La política de requeue se lee de `on_fail.requeue[]` en el YAML.

**Profile separado del Role**  
El conocimiento especializado vive en `profiles/<name>.md`, no en la clase Python. ContextBuilder lo inyecta en el system message.

**ContextBuilder filtra artefactos por step**  
Los agentes NO reciben el diccionario completo de task_artifacts. Solo lo que define `context_keys:` en el workflow YAML.

**BaseAgent recibe messages pre-construidos**  
`BaseAgent.run(messages)` es solo LLM caller + output parser. El Orchestrator llama a ContextBuilder antes.

**KB en dos capas**  
- Project Knowledge: `guidelines/` + `profiles/` — permanente  
- Task Artifacts: Redis (o in-memory) — por tarea, por ciclo QA

**QA etiqueta issues con profile responsable**  
Formato: `- [SEVERITY] descripción | agent: <role> | profile: <profile_name>`  
Sin el tag, el mecanismo de retroalimentación de profiles no funciona.

**`--permission-mode bypassPermissions` está bloqueado en root**  
No agregar ese flag al CLI — falla con rc=1 cuando el proceso corre como root.

---

## Preferencias de trabajo

- No usar agente Plan para análisis que se puede hacer directamente en la respuesta.
- No firmar commits con nombre de Claude ni Co-Authored-By.
- Explicar qué se va a editar antes de editar archivos de configuración críticos.
- Comentarios en GitHub: cortos, una línea.
- Commits: solo cuando el usuario confirme explícitamente.

---

## Estado actual

- MVP funcional. Demo exitosa con issue #12 (analyst + architect, workflow `analysis_only`).
- GitHub comment ✅ funcionando.
- Mover tarjeta en GitHub Project: requiere scope `project` en el GH_TOKEN.
- Workflows disponibles: `software_development`, `analysis_only`.
- Proveedor activo: `claude_code` (todos los agentes del team `dotnet-react-migration`).
