"""Analyst Agent — role instructions + output parser. Profile injected externally."""
from typing import Any
from agents.base.agent import BaseAgent
from orchestrator.llm.base import LLMResponse

SECTIONS = [
    "Problem Statement",
    "Functional Requirements",
    "User Stories",
    "Acceptance Criteria",
    "Out of Scope",
    "Assumptions",
]


class AnalystAgent(BaseAgent):
    ROLE_INSTRUCTIONS = """You are a Senior Business Analyst and Product Owner.

Analyze the given requirements and produce a structured output with these exact sections:

## Problem Statement
## Functional Requirements
## User Stories
## Acceptance Criteria
## Out of Scope
## Assumptions

Rules:
- Each User Story: "As a [role], I want [feature] so that [benefit]"
- Each Acceptance Criterion: Given / When / Then format
- If requirements are ambiguous, document your assumptions — do not infer silently
- Scope must be achievable in a single sprint (2 weeks)
- Do not make technical decisions — that belongs to the Architect
"""

    def _parse_output(self, response: LLMResponse) -> dict[str, Any]:
        artifacts = self._extract_sections(response.content, SECTIONS)
        artifacts["analyst_output"] = response.content
        return artifacts
