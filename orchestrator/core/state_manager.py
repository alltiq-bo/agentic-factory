"""
StateManager — tracks where each Task is in its lifecycle.

Backed by Redis when available; falls back to in-memory for development.
Updated by the Orchestrator via hooks on every engine transition.
"""
from __future__ import annotations
import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Optional

from orchestrator.core.models import TaskState, TaskStatus

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class StateManager:

    def __init__(self, redis_client=None, ttl: int = 86400):
        self._redis  = redis_client
        self._ttl    = ttl           # seconds — 24h default
        self._store: dict[str, TaskState] = {}

    async def create(self, state: TaskState) -> TaskState:
        state.created_at = _now()
        state.updated_at = state.created_at
        await self._save(state)
        logger.info("Task [%s] created — status=%s", state.task_id, state.status)
        return state

    async def transition(
        self,
        task_id: str,
        status: TaskStatus,
        *,
        current_step: Optional[str] = None,
        qa_cycle: Optional[int]     = None,
        error: Optional[str]        = None,
    ) -> TaskState:
        state = await self.get(task_id)
        if state is None:
            raise KeyError(f"Task '{task_id}' not found in StateManager")

        state.status     = status
        state.updated_at = _now()
        if current_step is not None: state.current_step = current_step
        if qa_cycle     is not None: state.qa_cycle     = qa_cycle
        if error        is not None: state.error        = error

        await self._save(state)
        logger.info(
            "Task [%s] → %s  step=%s  qa_cycle=%s",
            task_id, status.value, state.current_step, state.qa_cycle,
        )
        return state

    async def get(self, task_id: str) -> Optional[TaskState]:
        if self._redis:
            raw = await self._redis.get(f"task:{task_id}")
            if raw:
                data = json.loads(raw)
                data["status"] = TaskStatus(data["status"])
                return TaskState(**data)
        return self._store.get(task_id)

    async def _save(self, state: TaskState) -> None:
        data = asdict(state)
        data["status"] = state.status.value
        if self._redis:
            await self._redis.set(f"task:{state.task_id}", json.dumps(data), ex=self._ttl)
        self._store[state.task_id] = state
