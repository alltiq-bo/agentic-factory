"""Analyst Agent — breaks down requirements into structured user stories."""
import re
from typing import Any
from agents.base.agent import BaseAgent, LLMResponse, TaskContext


class AnalystAgent(BaseAgent):
    role = "analyst"
    system_prompt = """You are a senior Business Analyst and Product Owner.

Your job is to analyze requirements and produce:
1. A clear problem statement
2. Functional requirements as numbered list
3. User stories in format: "As a [role], I want [feature] so that [benefit]"
4. Acceptance criteria for each user story (Given/When/Then)
5. Out-of-scope items (what NOT to build)

Be concise and precise. Avoid ambiguity. If requirements are unclear, list your assumptions.

Output format (use these exact headers):
## Problem Statement
## Functional Requirements
## User Stories
## Acceptance Criteria
## Out of Scope
## Assumptions
"""

    def _parse_output(self, response: LLMResponse, context: TaskContext) -> dict[str, Any]:
        content = response.content
        artifacts: dict[str, Any] = {"user_stories_raw": content}

        # Extract sections by header
        sections = ["Problem Statement", "Functional Requirements", "User Stories",
                    "Acceptance Criteria", "Out of Scope", "Assumptions"]
        for section in sections:
            pattern = rf"## {section}\n(.*?)(?=\n## |\Z)"
            match = re.search(pattern, content, re.DOTALL)
            if match:
                key = section.lower().replace(" ", "_")
                artifacts[key] = match.group(1).strip()

        return artifacts
