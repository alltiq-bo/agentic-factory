"""
Knowledge Base Store — two-layer storage.

Layer 1: Project Knowledge  — permanent, loaded from guidelines/ and profiles/
Layer 2: Task Artifacts     — produced per task execution, stored in Redis

In development (no Redis), task artifacts live in memory.
"""
from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

GUIDELINES_DIR = Path(__file__).parents[1] / "guidelines"


class KnowledgeBase:

    def __init__(self, redis_client=None):
        self._redis = redis_client
        self._memory: dict[str, dict[str, Any]] = {}   # task_id → artifacts

    # ── Project Knowledge (read-only at runtime) ──────────────────────────

    def load_project_knowledge(self, sections: list[str] | None = None) -> dict[str, Any]:
        """
        Load permanent project knowledge from guidelines/.
        sections: e.g. ['decisions', 'standards'] — None loads all.
        """
        knowledge: dict[str, Any] = {}
        if not GUIDELINES_DIR.exists():
            return knowledge

        for md_file in GUIDELINES_DIR.rglob("*.md"):
            # Skip suggestion files
            if "suggestions" in md_file.name:
                continue
            section = md_file.parent.name
            if sections and section not in sections:
                continue
            key = f"{section}/{md_file.stem}"
            knowledge[key] = md_file.read_text(encoding="utf-8")

        logger.debug("Loaded %d project knowledge entries", len(knowledge))
        return knowledge

    # ── Task Artifacts (read/write per task) ──────────────────────────────

    async def write_artifacts(
        self,
        task_id: str,
        agent_role: str,
        artifacts: dict[str, Any],
    ) -> None:
        existing = await self.read_artifacts(task_id) or {}
        existing.update(artifacts)
        await self._save(task_id, existing)
        logger.debug(
            "KB write — task=%s role=%s keys=%s",
            task_id, agent_role, list(artifacts.keys()),
        )

    async def read_artifacts(self, task_id: str) -> Optional[dict[str, Any]]:
        if self._redis:
            raw = await self._redis.get(f"artifacts:{task_id}")
            return json.loads(raw) if raw else None
        return self._memory.get(task_id)

    async def _save(self, task_id: str, artifacts: dict[str, Any]) -> None:
        if self._redis:
            await self._redis.set(
                f"artifacts:{task_id}",
                json.dumps(artifacts, default=str),
                ex=86400,
            )
        self._memory[task_id] = artifacts

    # ── Profile suggestions (append-only) ─────────────────────────────────

    async def write_profile_suggestion(
        self,
        profile_name: str,
        suggestion: str,
        task_id: str,
    ) -> None:
        from orchestrator.core.profile_loader import append_suggestion
        append_suggestion(profile_name, f"[task: {task_id}]\n\n{suggestion}")
        logger.info("Profile suggestion appended for '%s'", profile_name)
