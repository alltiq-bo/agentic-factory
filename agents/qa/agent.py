"""QA Agent — role instructions + output parser + profile feedback trigger."""
from __future__ import annotations
import re
from typing import Any
from agents.base.agent import BaseAgent
from orchestrator.llm.base import LLMResponse

SECTIONS = [
    "Test Plan",
    "Test Cases",
    "Issues Found",
    "Coverage Assessment",
    "Profile Improvement Suggestions",
    "Verdict",
]


class QAAgent(BaseAgent):
    ROLE_INSTRUCTIONS = """You are a Senior QA Engineer and Test Architect.

Review ALL provided artifacts (user stories, architecture, backend code, frontend code)
and produce a structured validation report:

## Test Plan
## Test Cases
## Issues Found
## Coverage Assessment
## Profile Improvement Suggestions
## Verdict

Issue format:
  - [CRITICAL|HIGH|MEDIUM|LOW] <description> | agent: <responsible_agent> | profile: <profile_name>

Profile Improvement Suggestions format:
  - profile: <profile_name> | section: <section_title> | suggestion: <what to add or fix>

Verdict rules:
- PASS: no CRITICAL or HIGH issues remain
- FAIL: at least one CRITICAL or HIGH issue exists

Write exactly "VERDICT: PASS" or "VERDICT: FAIL" at the end of the Verdict section.
"""

    def _parse_output(self, response: LLMResponse) -> dict[str, Any]:
        artifacts = self._extract_sections(response.content, SECTIONS)
        artifacts["qa_output"] = response.content

        # ── Verdict ───────────────────────────────────────────────────────
        verdict_text = artifacts.get("verdict", "").upper()
        passed       = "VERDICT: PASS" in verdict_text
        artifacts["qa_passed"]  = passed
        artifacts["qa_verdict"] = "pass" if passed else "fail"

        # ── Structured issues ─────────────────────────────────────────────
        issues_text = artifacts.get("issues_found", "")
        issue_pattern = r"-\s+\[(CRITICAL|HIGH|MEDIUM|LOW)\]\s+(.+?)\s+\|\s+agent:\s+(\S+)\s+\|\s+profile:\s+(\S+)"
        issues = []
        for m in re.finditer(issue_pattern, issues_text, re.IGNORECASE):
            issues.append({
                "severity":           m.group(1).upper(),
                "description":        m.group(2).strip(),
                "responsible_agent":  m.group(3).strip(),
                "responsible_profile": m.group(4).strip(),
            })
        artifacts["qa_issues"] = issues

        # ── Profile improvement suggestions ───────────────────────────────
        suggestions_text = artifacts.get("profile_improvement_suggestions", "")
        sugg_pattern = r"-\s+profile:\s+(\S+)\s+\|\s+section:\s+(.+?)\s+\|\s+suggestion:\s+(.+)"
        suggestions  = []
        for m in re.finditer(sugg_pattern, suggestions_text, re.IGNORECASE):
            suggestions.append({
                "profile":    m.group(1).strip(),
                "section":    m.group(2).strip(),
                "suggestion": m.group(3).strip(),
            })
        artifacts["qa_profile_suggestions"] = suggestions

        return artifacts
