"""Architect Agent — produces system design and Architecture Decision Records."""
import re
from typing import Any
from agents.base.agent import BaseAgent, LLMResponse, TaskContext


class ArchitectAgent(BaseAgent):
    role = "architect"
    system_prompt = """You are a Principal Software Architect with deep expertise in
distributed systems, cloud-native design, and API design.

Based on the user stories and requirements provided, produce:
1. High-level system architecture (components and their responsibilities)
2. Technology stack decisions with rationale
3. API contracts (endpoints, request/response schemas)
4. Data model overview (entities and relationships)
5. Architecture Decision Records (ADRs) for key decisions
6. Non-functional requirements (scalability, security, observability)

Output format (use these exact headers):
## System Architecture
## Technology Stack
## API Contracts
## Data Model
## ADRs
## Non-Functional Requirements
## Risks and Mitigations
"""

    def _parse_output(self, response: LLMResponse, context: TaskContext) -> dict[str, Any]:
        content = response.content
        artifacts: dict[str, Any] = {"architecture_raw": content}

        sections = ["System Architecture", "Technology Stack", "API Contracts",
                    "Data Model", "ADRs", "Non-Functional Requirements", "Risks and Mitigations"]
        for section in sections:
            pattern = rf"## {section}\n(.*?)(?=\n## |\Z)"
            match = re.search(pattern, content, re.DOTALL)
            if match:
                key = section.lower().replace(" ", "_").replace("-", "_")
                artifacts[key] = match.group(1).strip()

        return artifacts
