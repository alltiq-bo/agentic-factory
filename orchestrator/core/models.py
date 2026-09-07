"""
Domain models — single source of truth for all core concepts.

Agent   → Role + Profile + LLM
Team    → Agents + Workflow
Workflow → Steps + Dependencies + Conditions + Retry/Requeue policies
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


# ── Enums ────────────────────────────────────────────────────────────────────

class TaskStatus(str, Enum):
    CREATED     = "created"
    ANALYZING   = "analyzing"
    DESIGNING   = "designing"
    DEVELOPING  = "developing"
    VALIDATING  = "validating"
    FIX_CYCLE   = "fix_cycle"
    DONE        = "done"
    FAILED      = "failed"
    ESCALATED   = "escalated"   # max QA cycles exceeded


class StepMode(str, Enum):
    SEQUENTIAL = "sequential"
    PARALLEL   = "parallel"


class AgentRunStatus(str, Enum):
    IDLE    = "idle"
    RUNNING = "running"
    DONE    = "done"
    FAILED  = "failed"


# ── LLM config ───────────────────────────────────────────────────────────────

@dataclass
class LLMConfig:
    provider:    str
    model:       str
    temperature: float = 0.7
    max_tokens:  int   = 4096
    timeout:     int   = 120
    extra:       dict  = field(default_factory=dict)


# ── Agent domain model ───────────────────────────────────────────────────────

@dataclass
class AgentDefinition:
    """Immutable definition of an agent as configured in a team YAML."""
    role:    str            # analyst | architect | backend_developer | frontend_developer | qa
    profile: str            # profile name → loaded from profiles/<name>.md
    llm:     LLMConfig


# ── Workflow domain model ────────────────────────────────────────────────────

@dataclass
class FailPolicy:
    """What to do when a step signals failure (e.g. QA FAIL)."""
    requeue:    list[str]   # step names to re-enqueue
    max_cycles: int = 3


@dataclass
class StepCondition:
    """Closed-vocabulary condition evaluated against task artifacts."""
    artifact: str
    operator: str           # eq | neq | contains | is_set | not_set
    value:    Any = None


@dataclass
class WorkflowStep:
    name:        str
    agent_role:  str
    mode:        StepMode = StepMode.SEQUENTIAL
    depends_on:  list[str] = field(default_factory=list)
    condition:   Optional[StepCondition] = None
    on_fail:     Optional[FailPolicy]    = None
    retry_max:   int = 2
    # Keys from task artifacts this step's agent should receive
    context_keys: list[str] = field(default_factory=list)
    # Prefixes of project_knowledge sections to include (None = all, [] = none)
    # e.g. ["decisions", "standards"] matches keys like "decisions/ADR-001-..."
    knowledge_sections: Optional[list[str]] = None


@dataclass
class WorkflowDefinition:
    name:  str
    steps: list[WorkflowStep]


# ── Team domain model ────────────────────────────────────────────────────────

@dataclass
class TeamDefinition:
    name:     str
    agents:   list[AgentDefinition]
    workflow: WorkflowDefinition


# ── Runtime: Task and artifacts ──────────────────────────────────────────────

@dataclass
class TaskState:
    task_id:      str
    project_id:   str
    status:       TaskStatus
    workflow_name: str
    current_step:  Optional[str] = None
    qa_cycle:      int = 0
    error:         Optional[str] = None
    created_at:    str = ""
    updated_at:    str = ""


@dataclass
class TaskContext:
    """
    Runtime context shared between all components during a workflow execution.

    project_knowledge → permanent KB (profiles, ADRs, standards)
    task_artifacts    → produced by agents in this task execution
    metadata          → engine internals, never sent to agents
    """
    task_id:          str
    project_id:       str
    input:            str
    project_knowledge: dict[str, Any] = field(default_factory=dict)
    task_artifacts:   dict[str, Any] = field(default_factory=dict)
    metadata:         dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    agent_role: str
    status:     AgentRunStatus
    output:     str
    artifacts:  dict[str, Any] = field(default_factory=dict)
    error:      Optional[str]  = None
    token_usage: Optional[dict] = None


@dataclass
class WorkflowRun:
    workflow_name: str
    task_id:       str
    results:       dict[str, AgentResult] = field(default_factory=dict)
    status:        str = "running"
    qa_cycle:      int = 0
    error:         Optional[str] = None
    token_usage:   dict[str, Any] = field(default_factory=dict)
    # token_usage shape:
    # {
    #   "step_name": {"input": N, "output": N},
    #   ...
    #   "total":     {"input": N, "output": N},
    # }
