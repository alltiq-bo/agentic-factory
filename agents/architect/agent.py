"""Architect Agent — role instructions + output parser. Profile injected externally."""
from typing import Any
from agents.base.agent import BaseAgent
from orchestrator.llm.base import LLMResponse

SECTIONS = [
    "System Architecture",
    "Technology Stack",
    "API Contracts",
    "Data Model",
    "ADRs",
    "Non-Functional Requirements",
    "Risks and Mitigations",
]


class ArchitectAgent(BaseAgent):
    ROLE_INSTRUCTIONS = """You are a Principal Software Architect.

Based on the provided user stories and requirements, produce a structured output with these exact sections:

## System Architecture
## Technology Stack
## API Contracts
## Data Model
## ADRs
## Non-Functional Requirements
## Risks and Mitigations

Rules:
- Every non-obvious decision must have an ADR (format: Context / Decision / Consequences)
- API contracts must be framework-agnostic (describe endpoints and schemas, not framework annotations)
- Prefer simplicity — document alternatives considered and why the simpler option was chosen
- Flag anything that contradicts the requirements as a Risk
"""

    def _parse_output(self, response: LLMResponse) -> dict[str, Any]:
        artifacts = self._extract_sections(response.content, SECTIONS)
        artifacts["architect_output"] = response.content
        return artifacts
