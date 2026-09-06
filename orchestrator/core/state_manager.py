"""
State Manager — tracks task lifecycle and persists state to Redis or in-memory.
"""
from __future__ import annotations
import json
import logging
from datetime import datetime, timezone
from dataclasses import asdict, dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class TaskState:
    task_id: str
    project_id: str
    status: str
    workflow_name: str
    qa_cycle: int = 0
    created_at: str = ""
    updated_at: str = ""
    error: Optional[str] = None
    current_step: Optional[str] = None

    def __post_init__(self):
        now = datetime.now(timezone.utc).isoformat()
        if not self.created_at:
            self.created_at = now
        self.updated_at = now


class StateManager:
    """
    In-memory state manager (swap backend for Redis in production).
    """

    def __init__(self, redis_client=None):
        self._redis = redis_client
        self._store: dict[str, TaskState] = {}

    async def create(self, state: TaskState) -> None:
        await self._save(state)
        logger.info("Task [%s] state created: %s", state.task_id, state.status)

    async def update(self, task_id: str, **kwargs) -> TaskState:
        state = await self.get(task_id)
        if not state:
            raise KeyError(f"Task {task_id} not found")
        for key, value in kwargs.items():
            setattr(state, key, value)
        state.updated_at = datetime.now(timezone.utc).isoformat()
        await self._save(state)
        logger.debug("Task [%s] state updated: %s", task_id, kwargs)
        return state

    async def get(self, task_id: str) -> Optional[TaskState]:
        if self._redis:
            raw = await self._redis.get(f"task:{task_id}")
            if raw:
                return TaskState(**json.loads(raw))
        return self._store.get(task_id)

    async def _save(self, state: TaskState) -> None:
        if self._redis:
            await self._redis.set(
                f"task:{state.task_id}",
                json.dumps(asdict(state)),
                ex=86400,  # 24h TTL
            )
        self._store[state.task_id] = state
