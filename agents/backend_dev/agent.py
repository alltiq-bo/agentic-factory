"""Backend Developer Agent — implements APIs, services, and data layer."""
import re
from typing import Any
from agents.base.agent import BaseAgent, LLMResponse, TaskContext


class BackendDevAgent(BaseAgent):
    role = "backend_dev"
    system_prompt = """You are a Senior Backend Engineer specializing in Python,
REST APIs, and database design.

Based on the architecture and user stories provided, produce:
1. Implementation plan (ordered list of tasks)
2. Core code for the main service/API (production-ready, not pseudocode)
3. Database schema (SQL or ORM models)
4. Unit test stubs (pytest) for each endpoint/function
5. Environment variables and configuration needed
6. Docker setup for the service

Prioritize: correctness, security (no injection, proper auth), and testability.
Use type hints. No unnecessary abstractions.

Output format (use these exact headers):
## Implementation Plan
## Core Code
## Database Schema
## Test Stubs
## Configuration
## Docker Setup
"""

    def _parse_output(self, response: LLMResponse, context: TaskContext) -> dict[str, Any]:
        content = response.content
        artifacts: dict[str, Any] = {"backend_implementation_raw": content}

        sections = ["Implementation Plan", "Core Code", "Database Schema",
                    "Test Stubs", "Configuration", "Docker Setup"]
        for section in sections:
            pattern = rf"## {section}\n(.*?)(?=\n## |\Z)"
            match = re.search(pattern, content, re.DOTALL)
            if match:
                key = section.lower().replace(" ", "_")
                artifacts[f"backend_{key}"] = match.group(1).strip()

        return artifacts
