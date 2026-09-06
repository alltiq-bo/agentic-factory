"""Frontend Developer Agent — implements UI components and client-side logic."""
import re
from typing import Any
from agents.base.agent import BaseAgent, LLMResponse, TaskContext


class FrontendDevAgent(BaseAgent):
    role = "frontend_dev"
    system_prompt = """You are a Senior Frontend Engineer specializing in
React, TypeScript, and modern UI/UX patterns.

Based on the architecture, API contracts, and user stories provided, produce:
1. Component tree (hierarchy and responsibilities)
2. Core components implementation (React + TypeScript)
3. API integration layer (hooks/services that call backend)
4. State management approach
5. Routing structure
6. Unit test stubs (Vitest/Jest + React Testing Library)

Prioritize: accessibility (WCAG AA), performance, and type safety.
No unnecessary dependencies.

Output format (use these exact headers):
## Component Tree
## Core Components
## API Integration
## State Management
## Routing
## Test Stubs
"""

    def _parse_output(self, response: LLMResponse, context: TaskContext) -> dict[str, Any]:
        content = response.content
        artifacts: dict[str, Any] = {"frontend_implementation_raw": content}

        sections = ["Component Tree", "Core Components", "API Integration",
                    "State Management", "Routing", "Test Stubs"]
        for section in sections:
            pattern = rf"## {section}\n(.*?)(?=\n## |\Z)"
            match = re.search(pattern, content, re.DOTALL)
            if match:
                key = section.lower().replace(" ", "_")
                artifacts[f"frontend_{key}"] = match.group(1).strip()

        return artifacts
