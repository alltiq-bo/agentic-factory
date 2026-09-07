"""
Config Loader — parses YAML team and workflow files into domain models.

Team YAML schema (teams/*.yaml):
  team:
    name: dotnet-react-migration
  agents:
    - role: analyst
      profile: software_analysis
      llm: { provider, model, temperature, max_tokens }
  workflow: software_development     # references workflows/<name>.yaml

Workflow YAML schema (workflows/*.yaml):
  name: software_development
  steps:
    - name: analyze_requirements
      agent_role: analyst
      mode: sequential
      depends_on: []
      context_keys: []
      retry_max: 2
      on_fail:                       # optional
        requeue: [step_a, step_b]
        max_cycles: 3
      condition:                     # optional
        artifact: some_key
        operator: eq
        value: "expected"
"""
from __future__ import annotations
import os
import yaml
from pathlib import Path
from typing import Any

from orchestrator.core.models import (
    AgentDefinition, FailPolicy, LLMConfig,
    StepCondition, StepMode,
    TeamDefinition, WorkflowDefinition, WorkflowStep,
)

TEAMS_DIR     = Path(__file__).parents[2] / "teams"
WORKFLOWS_DIR = Path(__file__).parents[2] / "workflows"


def _resolve_base_dir(base_dir: Path | None) -> Path | None:
    """Return base_dir if provided; otherwise fall back to AGENTIC_PROJECT_DIR env var."""
    if base_dir is not None:
        return base_dir
    env_val = os.environ.get("AGENTIC_PROJECT_DIR")
    return Path(env_val) if env_val else None


def _load_yaml(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _parse_llm(raw: dict) -> LLMConfig:
    return LLMConfig(
        provider=raw["provider"],
        model=raw["model"],
        temperature=raw.get("temperature", 0.7),
        max_tokens=raw.get("max_tokens", 4096),
        timeout=raw.get("timeout", 120),
        extra=raw.get("extra", {}),
    )


def _parse_condition(raw: dict | None) -> StepCondition | None:
    if not raw:
        return None
    return StepCondition(
        artifact=raw["artifact"],
        operator=raw["operator"],
        value=raw.get("value"),
    )


def _parse_on_fail(raw: dict | None) -> FailPolicy | None:
    if not raw:
        return None
    return FailPolicy(
        requeue=raw.get("requeue", []),
        max_cycles=raw.get("max_cycles", 3),
    )


def _parse_workflow(raw: dict) -> WorkflowDefinition:
    steps = []
    for s in raw.get("steps", []):
        steps.append(WorkflowStep(
            name=s["name"],
            agent_role=s["agent_role"],
            mode=StepMode(s.get("mode", "sequential")),
            depends_on=s.get("depends_on", []),
            condition=_parse_condition(s.get("condition")),
            on_fail=_parse_on_fail(s.get("on_fail")),
            retry_max=s.get("retry_max", 2),
            context_keys=s.get("context_keys", []),
            knowledge_sections=s.get("knowledge_sections", None),
            include_input=s.get("include_input", "full"),
            summary_artifact=s.get("summary_artifact", None),
        ))
    return WorkflowDefinition(name=raw["name"], steps=steps)


def load_workflow(name: str, base_dir: Path | None = None) -> WorkflowDefinition:
    """Load a workflow YAML by name.

    If *base_dir* is provided (or ``AGENTIC_PROJECT_DIR`` env var is set),
    ``<base_dir>/.agentiq/<name>.yaml`` is tried first before falling back to
    the factory ``workflows/`` directory.
    """
    resolved = _resolve_base_dir(base_dir)
    if resolved is not None:
        candidate = resolved / ".agentiq" / f"{name}.yaml"
        if candidate.exists():
            return _parse_workflow(_load_yaml(candidate))
    path = WORKFLOWS_DIR / f"{name}.yaml"
    return _parse_workflow(_load_yaml(path))


def load_team(team_name: str, base_dir: Path | None = None) -> TeamDefinition:
    """Load a team YAML by name.

    If *base_dir* is provided (or ``AGENTIC_PROJECT_DIR`` env var is set),
    ``<base_dir>/.agentiq/team.yaml`` is tried first before falling back to
    the factory ``teams/`` directory.
    """
    resolved = _resolve_base_dir(base_dir)
    if resolved is not None:
        candidate = resolved / ".agentiq" / "team.yaml"
        if candidate.exists():
            path = candidate
        else:
            path = TEAMS_DIR / f"{team_name}.yaml"
    else:
        path = TEAMS_DIR / f"{team_name}.yaml"
    raw  = _load_yaml(path)

    agents = [
        AgentDefinition(
            role=a["role"],
            profile=a["profile"],
            llm=_parse_llm(a["llm"]),
        )
        for a in raw.get("agents", [])
    ]

    workflow_ref = raw.get("workflow")
    if isinstance(workflow_ref, str):
        workflow = load_workflow(workflow_ref, base_dir=base_dir)
    else:
        workflow = _parse_workflow(workflow_ref)

    return TeamDefinition(
        name=raw["team"]["name"],
        agents=agents,
        workflow=workflow,
    )
