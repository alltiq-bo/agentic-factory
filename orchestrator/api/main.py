"""
FastAPI application — Orchestrator API.

POST /tasks        → submit a task (texto libre o referencia a GitHub issue)
POST /tasks/sync   → igual pero espera el resultado
GET  /tasks/{id}   → consultar estado
GET  /health       → liveness check
"""
from __future__ import annotations
import os
import logging

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from orchestrator.orchestrator import Orchestrator
from orchestrator.core.state_manager import StateManager
from knowledge_base.store import KnowledgeBase

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Agentic Factory",
    description="AI agent team orchestration platform",
    version="0.1.0",
)

# ── Dependency setup ──────────────────────────────────────────────────────

_state_manager: StateManager | None = None
_knowledge_base: KnowledgeBase | None = None


@app.on_event("startup")
async def startup():
    global _state_manager, _knowledge_base

    redis_client = None
    redis_url = os.environ.get("REDIS_URL")
    if redis_url:
        try:
            import redis.asyncio as aioredis
            redis_client = aioredis.from_url(redis_url, decode_responses=True)
            await redis_client.ping()
            logger.info("Redis connected: %s", redis_url)
        except Exception as e:
            logger.warning("Redis unavailable (%s) — using in-memory fallback", e)
            redis_client = None

    _state_manager  = StateManager(redis_client=redis_client)
    _knowledge_base = KnowledgeBase(redis_client=redis_client)
    logger.info("Agentic Factory started — team=%s",
                os.environ.get("TEAM_CONFIG", "dotnet-react-migration"))


def get_orchestrator() -> Orchestrator:
    team = os.environ.get("TEAM_CONFIG", "dotnet-react-migration")
    return Orchestrator(
        state_manager  = _state_manager,
        knowledge_base = _knowledge_base,
        team_name      = team,
    )


# ── GitHub issue fetcher ──────────────────────────────────────────────────

class GitHubIssueRef(BaseModel):
    repo:   str = Field(..., description="owner/repo — ej. vega-bo/web.agro.nt")
    number: int = Field(..., description="Número del issue")


async def fetch_github_issue(ref: GitHubIssueRef) -> str:
    """
    Fetcha el issue de GitHub y retorna un texto listo para el agente.
    Usa GH_TOKEN si está disponible (necesario para repos privados).
    """
    url = f"https://api.github.com/repos/{ref.repo}/issues/{ref.number}"
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, headers=headers)

    if resp.status_code == 404:
        raise HTTPException(status_code=404,
                            detail=f"Issue #{ref.number} no encontrado en {ref.repo}")
    if resp.status_code == 401:
        raise HTTPException(status_code=401,
                            detail="GH_TOKEN requerido para acceder a este repo")
    resp.raise_for_status()

    data = resp.json()
    title  = data.get("title", "")
    body   = data.get("body") or ""
    labels = [l["name"] for l in data.get("labels", [])]
    label_str = f"[{', '.join(labels)}]" if labels else ""

    return (
        f"GitHub Issue #{ref.number} — {ref.repo} {label_str}\n"
        f"## {title}\n\n"
        f"{body}"
    )


# ── Request / Response models ─────────────────────────────────────────────

class TaskRequest(BaseModel):
    input:        str | None          = Field(default=None, description="Texto libre de la tarea")
    github_issue: GitHubIssueRef | None = Field(default=None, description="Referencia a un issue de GitHub")
    team:         str | None          = Field(default=None, description="Nombre del team (override de TEAM_CONFIG)")
    project_id:   str                 = Field(default="default", description="Identificador del proyecto")
    task_id:      str | None          = Field(default=None, description="ID de tarea (se genera si se omite)")

    def model_post_init(self, __context):
        if not self.input and not self.github_issue:
            raise ValueError("Se requiere 'input' o 'github_issue'")


class TaskResponse(BaseModel):
    task_id:  str
    status:   str
    team:     str
    source:   str   # "text" | "github_issue"


class TaskStatusResponse(BaseModel):
    task_id:      str
    status:       str
    current_step: str | None
    qa_cycle:     int
    error:        str | None
    created_at:   str
    updated_at:   str


# ── Helpers ───────────────────────────────────────────────────────────────

async def resolve_input(request: TaskRequest) -> str:
    if request.github_issue:
        logger.info("Fetching GitHub issue %s#%d",
                    request.github_issue.repo, request.github_issue.number)
        return await fetch_github_issue(request.github_issue)
    return request.input


def resolve_team(request: TaskRequest) -> str:
    return request.team or os.environ.get("TEAM_CONFIG", "dotnet-react-migration")


# ── Routes ────────────────────────────────────────────────────────────────

@app.post("/tasks", response_model=TaskResponse, status_code=202)
async def submit_task(request: TaskRequest):
    """Envía una tarea al equipo de agentes. Retorna inmediatamente con task_id."""
    import asyncio
    input_text = await resolve_input(request)
    team       = resolve_team(request)
    orch       = Orchestrator(
        state_manager  = _state_manager,
        knowledge_base = _knowledge_base,
        team_name      = team,
    )

    github_issue = request.github_issue.model_dump() if request.github_issue else None

    asyncio.create_task(
        orch.run_task(
            input_text   = input_text,
            project_id   = request.project_id,
            task_id      = request.task_id,
            github_issue = github_issue,
        )
    )

    return TaskResponse(
        task_id = request.task_id or "pending",
        status  = "created",
        team    = team,
        source  = "github_issue" if request.github_issue else "text",
    )


@app.post("/tasks/sync", response_model=dict)
async def submit_task_sync(request: TaskRequest):
    """Envía una tarea y espera el resultado completo."""
    input_text = await resolve_input(request)
    team       = resolve_team(request)
    orch       = Orchestrator(
        state_manager  = _state_manager,
        knowledge_base = _knowledge_base,
        team_name      = team,
    )

    github_issue = request.github_issue.model_dump() if request.github_issue else None

    run = await orch.run_task(
        input_text   = input_text,
        project_id   = request.project_id,
        task_id      = request.task_id,
        github_issue = github_issue,
    )

    return {
        "task_id":   run.task_id,
        "status":    run.status,
        "team":      team,
        "qa_cycle":  run.qa_cycle,
        "error":     run.error,
        "steps_run": list(run.results.keys()),
        "results":   {
            step: {
                "role":   r.agent_role,
                "output": r.output,
            }
            for step, r in run.results.items()
        },
    }


@app.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task(task_id: str):
    state = await _state_manager.get(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    return TaskStatusResponse(
        task_id      = state.task_id,
        status       = state.status.value,
        current_step = state.current_step,
        qa_cycle     = state.qa_cycle,
        error        = state.error,
        created_at   = state.created_at,
        updated_at   = state.updated_at,
    )


@app.get("/health")
async def health():
    return {"status": "ok"}
