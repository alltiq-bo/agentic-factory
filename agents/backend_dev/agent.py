"""Backend Developer Agent — role instructions + output parser. Profile injected externally."""
from typing import Any
from agents.base.agent import BaseAgent
from orchestrator.llm.base import LLMResponse

SECTIONS = [
    "Implementation Plan",
    "Core Code",
    "Database Schema",
    "Test Stubs",
    "Configuration",
    "Docker Setup",
]


class BackendDevAgent(BaseAgent):
    ROLE_INSTRUCTIONS = """You are a Senior Backend Engineer.

Based on the provided architecture, API contracts, and user stories, produce:

## Implementation Plan
## Core Code
## Database Schema
## Test Stubs
## Configuration
## Docker Setup

Rules:
- Write production-ready code, not pseudocode
- Use type hints throughout
- No SQL injection, no hardcoded secrets, validate at system boundaries only
- Test stubs must cover every endpoint and every public function
- If a QA fix cycle is active, address each reported issue explicitly before producing new code
"""

    def _parse_output(self, response: LLMResponse) -> dict[str, Any]:
        artifacts = self._extract_sections(response.content, SECTIONS)
        artifacts["backend_output"] = response.content
        return artifacts
