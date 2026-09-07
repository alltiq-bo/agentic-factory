# CLAUDE.md — Agentic Factory

Contexto del proyecto para cualquier sesión de Claude Code.

---

## Proyecto

**Agentic Factory** es la plataforma/producto. Orquesta equipos de agentes AI configurables por YAML.
Los proyectos que la usan son consumidores — no definen la arquitectura del Factory.

El core debe mantenerse domain-agnostic, stack-agnostic y project-agnostic.
La tecnología del proyecto target vive exclusivamente en: `teams/`, `profiles/`, `workflows/`, `.agentic/`.

**Repo:** alltiq-bo/agentic-factory

---

## Cómo correr

Redis en Docker, orquestador en host (claude_code no funciona dentro de Docker — OAuth ligado a sesión local):

```bash
docker compose up redis -d
source .env && export $(grep -v '^#' .env | xargs)
nohup python3 -m uvicorn orchestrator.api.main:app --host 0.0.0.0 --port 8000 > /tmp/orchestrator.log 2>&1 &
```

CLI:

```bash
python3 agentiq doctor                                        # verificar entorno
python3 agentiq run --issue owner/repo#N --workflow analysis_only
python3 agentiq logs
python3 agentiq status <task_id>
python3 agentiq help                                          # referencia completa
```

---

## Variables de entorno (.env)

| Variable | Descripción |
|----------|-------------|
| `GH_TOKEN` | Personal Access Token GitHub — scopes: `repo` + `project` |
| `TEAM_CONFIG` | Nombre del team YAML |
| `CLAUDE_BIN` | Path al binario claude |
| `CLAUDE_CONFIG_DIR` | Sesión Claude a usar (ej. `~/.claude-personal`) |
| `CLAUDE_ADD_DIRS` | Dirs accesibles por subprocess, separados por `:` |
| `CLAUDE_TIMEOUT` | Timeout en segundos por llamada al CLI (default: 600) |
| `AGENTIC_PROJECT_DIR` | Dir del proyecto con `.agentic/` — override de config |

---

## Decisiones de arquitectura — NO revertir

**Agentic Factory es domain/stack/project-agnostic**
El core no tiene referencias a tecnologías, roles de dominio ni proyectos específicos.
Todo lo específico va en teams, profiles, workflows o `.agentic/` del proyecto consumidor.

**WorkflowEngine es domain-agnóstico**
El engine NO tiene `if step.agent_role == "qa"` ni nombres hardcodeados.
La política de requeue se lee de `on_fail.requeue[]` en el YAML.

**Profile separado del Role**
El conocimiento especializado vive en `profiles/<name>.md`, no en la clase Python.
ContextBuilder lo inyecta en el system message.

**ContextBuilder filtra artefactos por step**
Los agentes NO reciben el diccionario completo de task_artifacts.
Solo lo que define `context_keys:` en el workflow YAML.

**BaseAgent recibe messages pre-construidos**
`BaseAgent.run(messages)` es solo LLM caller + output parser.
El Orchestrator llama a ContextBuilder antes.

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
- Preguntar antes de hacer commit o push.

---

## Estado actual

- MVP funcional. GitHub comment ✅. Mover tarjeta: requiere scope `project` en GH_TOKEN.
- Workflows: `software_development`, `analysis_only`.
- Proveedor activo en teams de ejemplo: `claude_code`.
- CLI `agentiq`: `doctor` · `validate` · `init` · `run` · `status` · `logs` · `help` · `team/workflow/profile list`.
- `ConfigLoader` soporta `AGENTIC_PROJECT_DIR` para config externa en `.agentic/`.
