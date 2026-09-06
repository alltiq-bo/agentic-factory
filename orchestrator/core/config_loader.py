"""
Config Loader — reads team and workflow YAML configs and builds runtime objects.
"""
from __future__ import annotations
import yaml
from pathlib import Path
from typing import Any

from orchestrator.llm import LLMConfig
from orchestrator.core.workflow_engine import WorkflowDefinition, WorkflowStep, StepMode


def load_yaml(path: str | Path) -> dict[str, Any]:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def parse_llm_config(raw: dict) -> LLMConfig:
    return LLMConfig(
        provider=raw["provider"],
        model=raw["model"],
        temperature=raw.get("temperature", 0.7),
        max_tokens=raw.get("max_tokens", 4096),
        timeout=raw.get("timeout", 120),
        extra=raw.get("extra", {}),
    )


def parse_workflow(raw: dict) -> WorkflowDefinition:
    steps = []
    for step_raw in raw.get("steps", []):
        steps.append(WorkflowStep(
            name=step_raw["name"],
            agent_role=step_raw["agent_role"],
            mode=StepMode(step_raw.get("mode", "sequential")),
            depends_on=step_raw.get("depends_on", []),
            condition=step_raw.get("condition"),
            on_fail=step_raw.get("on_fail"),
            retry_max=step_raw.get("retry_max", 2),
            extra_prompt=step_raw.get("extra_prompt", ""),
        ))
    return WorkflowDefinition(
        name=raw["name"],
        steps=steps,
        max_qa_cycles=raw.get("max_qa_cycles", 3),
    )


def load_team_config(team_config_path: str | Path) -> dict[str, Any]:
    """
    Returns a dict with:
    - agents: {role: LLMConfig}
    - workflow: WorkflowDefinition
    - settings: dict
    """
    raw = load_yaml(team_config_path)

    agent_configs = {}
    for role, cfg in raw.get("agents", {}).items():
        agent_configs[role] = parse_llm_config(cfg["llm"])

    workflow = parse_workflow(raw["workflow"])

    return {
        "agents": agent_configs,
        "workflow": workflow,
        "settings": raw.get("settings", {}),
    }
