"""
Profile Loader — loads agent profile documents from the profiles/ directory.

A profile is a Markdown file containing the specialized knowledge
injected into an agent's context. It is external to the code —
updating a profile never requires a code change.
"""
from __future__ import annotations
import logging
from pathlib import Path
from functools import lru_cache

logger = logging.getLogger(__name__)

PROFILES_DIR = Path(__file__).parents[2] / "profiles"


@lru_cache(maxsize=32)
def load_profile(profile_name: str) -> str:
    """
    Load profile content by name.
    profile_name: e.g. 'dotnet8' → reads profiles/dotnet8.md
    """
    path = PROFILES_DIR / f"{profile_name}.md"
    if not path.exists():
        logger.warning("Profile '%s' not found at %s", profile_name, path)
        return f"[Profile '{profile_name}' not found]"
    content = path.read_text(encoding="utf-8")
    logger.debug("Loaded profile '%s' (%d chars)", profile_name, len(content))
    return content


def profile_exists(profile_name: str) -> bool:
    return (PROFILES_DIR / f"{profile_name}.md").exists()


def append_suggestion(profile_name: str, suggestion: str) -> None:
    """
    Write a profile improvement suggestion to profiles/<name>.suggestions.md.
    Human reviews and approves before merging into the active profile.
    """
    path = PROFILES_DIR / f"{profile_name}.suggestions.md"
    with open(path, "a", encoding="utf-8") as f:
        from datetime import datetime, timezone
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        f.write(f"\n\n---\n## Suggestion — {ts}\n\n{suggestion}\n")
    logger.info("Profile suggestion written to %s", path)


def invalidate_cache(profile_name: str) -> None:
    """Call after approving a suggestion and updating the active profile."""
    load_profile.cache_clear()
    logger.info("Profile cache cleared for '%s'", profile_name)
