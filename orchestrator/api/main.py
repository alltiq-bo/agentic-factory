"""
FastAPI application — Orchestrator API.

POST /tasks        → submit a new task
GET  /tasks/{id}   → query task status
GET  /health       → liveness check
"""
from __future__ import annotations
import os
import logging

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


# ── Request / Response models ─────────────────────────────────────────────

class TaskRequest(BaseModel):
    input:      str = Field(..., description="Task description or GitHub issue body")
    project_id: str = Field(default="default", description="Project identifier")
    task_id:    str | None = Field(default=None, description="Optional task ID (generated if omitted)")


class TaskResponse(BaseModel):
    task_id:  str
    status:   str
    workflow: str


class TaskStatusResponse(BaseModel):
    task_id:      str
    status:       str
    current_step: str | None
    qa_cycle:     int
    error:        str | None
    created_at:   str
    updated_at:   str


# ── Routes ────────────────────────────────────────────────────────────────

@app.post("/tasks", response_model=TaskResponse, status_code=202)
async def submit_task(request: TaskRequest):
    """Submit a task to the agent team. Returns immediately with task_id."""
    import asyncio
    orch = get_orchestrator()

    # Run workflow in background — caller polls GET /tasks/{id}
    asyncio.create_task(
        orch.run_task(
            input_text = request.input,
            project_id = request.project_id,
            task_id    = request.task_id,
        )
    )

    # The task_id is set synchronously before the background task runs
    task_id = request.task_id or "pending"  # runner sets it after create_task
    return TaskResponse(
        task_id  = task_id,
        status   = "created",
        workflow = os.environ.get("TEAM_CONFIG", "dotnet-react-migration"),
    )


@app.post("/tasks/sync", response_model=dict)
async def submit_task_sync(request: TaskRequest):
    """Submit a task and wait for completion. Returns full workflow run."""
    orch = get_orchestrator()
    run  = await orch.run_task(
        input_text = request.input,
        project_id = request.project_id,
        task_id    = request.task_id,
    )
    return {
        "task_id":      run.task_id,
        "status":       run.status,
        "qa_cycle":     run.qa_cycle,
        "error":        run.error,
        "steps_run":    list(run.results.keys()),
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
