"""QA Agent — validates implementation against requirements, emits pass/fail verdict."""
import re
from typing import Any
from agents.base.agent import BaseAgent, LLMResponse, TaskContext


class QAAgent(BaseAgent):
    role = "qa"
    system_prompt = """You are a Senior QA Engineer and Test Architect.

Your job is to validate that the implementation meets the original requirements.

Review all provided artifacts (user stories, architecture, backend code, frontend code)
and produce:
1. Test plan (scope, test types, coverage targets)
2. Test cases (ID, description, steps, expected result)
3. Issues found (severity: critical/high/medium/low, description, affected component)
4. Coverage assessment (what is and isn't covered)
5. Final verdict: PASS or FAIL with justification

A PASS verdict means: all critical/high issues are resolved and acceptance criteria are met.
A FAIL verdict means: at least one critical or high severity issue remains.

Output format (use these exact headers):
## Test Plan
## Test Cases
## Issues Found
## Coverage Assessment
## Verdict
"""

    def _parse_output(self, response: LLMResponse, context: TaskContext) -> dict[str, Any]:
        content = response.content
        artifacts: dict[str, Any] = {"qa_report_raw": content}

        sections = ["Test Plan", "Test Cases", "Issues Found",
                    "Coverage Assessment", "Verdict"]
        for section in sections:
            pattern = rf"## {section}\n(.*?)(?=\n## |\Z)"
            match = re.search(pattern, content, re.DOTALL)
            if match:
                key = section.lower().replace(" ", "_")
                artifacts[f"qa_{key}"] = match.group(1).strip()

        # Determine pass/fail from verdict section
        verdict_text = artifacts.get("qa_verdict", "").upper()
        artifacts["qa_status"] = "pass" if "PASS" in verdict_text else "fail"

        # Extract issues list
        issues_text = artifacts.get("qa_issues_found", "")
        critical_pattern = r"(?i)(critical|high)[^\n]*\n([^\n]+)"
        artifacts["qa_critical_issues"] = re.findall(critical_pattern, issues_text)

        return artifacts
