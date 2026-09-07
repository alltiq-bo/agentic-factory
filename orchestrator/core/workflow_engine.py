"""
Workflow Engine — executes a WorkflowDefinition against a TaskContext.

The engine is domain-agnostic: it knows nothing about QA, developers,
or any specific agent role. All policies (requeue, max cycles) are
read from the WorkflowDefinition provided at runtime.
"""
from __future__ import annotations
import asyncio
import logging
from typing import Callable, Optional

from orchestrator.core.models import (
    AgentResult, AgentRunStatus, StepCondition,
    TaskContext, WorkflowDefinition, WorkflowRun, WorkflowStep,
    StepMode,
)

logger = logging.getLogger(__name__)

# Callable type aliases for hooks
StepHook = Callable[[WorkflowStep, TaskContext], None]
ResultHook = Callable[[WorkflowStep, AgentResult, TaskContext], None]


class WorkflowEngine:
    """
    Executes workflow steps in dependency order, with parallel fan-out,
    condition evaluation, and config-driven requeue policies.

    Agent execution is delegated to the runner callable injected at init,
    keeping the engine decoupled from BaseAgent implementations.
    """

    def __init__(
        self,
        runner: Callable[[WorkflowStep, TaskContext, int], AgentResult],
        on_step_start:    Optional[StepHook]   = None,
        on_step_complete: Optional[ResultHook] = None,
        on_step_fail:     Optional[ResultHook] = None,
    ):
        """
        runner: async callable(step, context, qa_cycle) → AgentResult
                Injected by Orchestrator — owns agent instantiation.
        """
        self._runner          = runner
        self._on_step_start   = on_step_start
        self._on_step_complete = on_step_complete
        self._on_step_fail    = on_step_fail

    async def execute(
        self,
        workflow: WorkflowDefinition,
        context: TaskContext,
    ) -> WorkflowRun:
        run     = WorkflowRun(workflow_name=workflow.name, task_id=context.task_id)
        completed: set[str] = set()
        cycle_counts: dict[str, int] = {}   # step_name → requeue cycles used
        pending = list(workflow.steps)

        logger.info("Workflow [%s] started — task %s", workflow.name, context.task_id)

        while pending:
            ready = self._ready_steps(pending, completed, context)

            if not ready:
                logger.error(
                    "Deadlock — no ready steps. completed=%s pending=%s",
                    completed, [s.name for s in pending],
                )
                run.status = "deadlock"
                break

            parallel   = [s for s in ready if s.mode == StepMode.PARALLEL]
            sequential = [s for s in ready if s.mode == StepMode.SEQUENTIAL]

            # ── parallel fan-out ────────────────────────────────────────────
            if parallel:
                results = await asyncio.gather(
                    *[self._run_step(s, context, run.qa_cycle) for s in parallel]
                )
                for step, result in zip(parallel, results):
                    run.results[step.name] = result
                    self._store_artifacts(step, result, context)
                    self._accumulate_tokens(step, result, run)
                    if result.status == AgentRunStatus.DONE:
                        completed.add(step.name)
                    else:
                        self._apply_failure(step, result, run)
                pending = [s for s in pending if s not in parallel]

            # ── sequential steps ────────────────────────────────────────────
            for step in list(sequential):
                if step not in pending:
                    continue

                result = await self._run_step(step, context, run.qa_cycle)
                run.results[step.name] = result
                self._store_artifacts(step, result, context)
                self._accumulate_tokens(step, result, run)

                if result.status == AgentRunStatus.DONE:
                    completed.add(step.name)

                    # ── config-driven requeue (e.g. QA FAIL) ───────────────
                    if step.on_fail and self._step_signals_failure(step, result, context):
                        cycle_counts[step.name] = cycle_counts.get(step.name, 0) + 1
                        run.qa_cycle            = cycle_counts[step.name]

                        if cycle_counts[step.name] >= step.on_fail.max_cycles:
                            run.status = "escalated"
                            run.error  = (
                                f"Step '{step.name}' triggered requeue "
                                f"{cycle_counts[step.name]} times (max={step.on_fail.max_cycles})"
                            )
                            return run

                        logger.info(
                            "Step [%s] signalled failure — requeue cycle %d/%d",
                            step.name, cycle_counts[step.name], step.on_fail.max_cycles,
                        )
                        for requeue_name in step.on_fail.requeue:
                            completed.discard(requeue_name)
                            requeue_step = next(
                                (s for s in workflow.steps if s.name == requeue_name), None
                            )
                            if requeue_step and requeue_step not in pending:
                                pending.append(requeue_step)

                        # Remove current step from completed so it re-runs after requeue
                        completed.discard(step.name)
                        pending.remove(step)
                        break   # restart outer while with new pending

                else:
                    self._apply_failure(step, result, run)
                    if run.status == "failed":
                        return run

                pending.remove(step)

        if run.status == "running":
            run.status = "done"
            logger.info("Workflow [%s] done — task %s", workflow.name, context.task_id)

        return run

    # ── helpers ──────────────────────────────────────────────────────────────

    def _ready_steps(
        self,
        pending: list[WorkflowStep],
        completed: set[str],
        context: TaskContext,
    ) -> list[WorkflowStep]:
        return [
            s for s in pending
            if all(dep in completed for dep in s.depends_on)
            and self._eval_condition(s.condition, context)
        ]

    async def _run_step(
        self,
        step: WorkflowStep,
        context: TaskContext,
        qa_cycle: int,
    ) -> AgentResult:
        if self._on_step_start:
            self._on_step_start(step, context)

        logger.info("Step [%s] → agent_role=%s", step.name, step.agent_role)
        result = await self._runner(step, context, qa_cycle)

        if result.status == AgentRunStatus.DONE and self._on_step_complete:
            self._on_step_complete(step, result, context)
        elif result.status == AgentRunStatus.FAILED and self._on_step_fail:
            self._on_step_fail(step, result, context)

        return result

    def _store_artifacts(
        self,
        step: WorkflowStep,
        result: AgentResult,
        context: TaskContext,
    ) -> None:
        """Write agent artifacts into task_artifacts keyed by role."""
        for key, value in result.artifacts.items():
            context.task_artifacts[key] = value
        # Always store the raw output under a predictable key
        context.task_artifacts[f"{step.agent_role}_output"] = result.output
        # Promote summary_artifact to context.summary if configured
        if step.summary_artifact and step.summary_artifact in context.task_artifacts:
            context.summary = str(context.task_artifacts[step.summary_artifact])

    def _accumulate_tokens(
        self,
        step: WorkflowStep,
        result: AgentResult,
        run: WorkflowRun,
    ) -> None:
        """Accumulate token usage per step and in running total."""
        usage = result.token_usage or {}
        inp = usage.get("input") or 0
        out = usage.get("output") or 0
        run.token_usage[step.name] = {"input": inp, "output": out}
        total = run.token_usage.get("total", {"input": 0, "output": 0})
        run.token_usage["total"] = {
            "input":  total["input"]  + inp,
            "output": total["output"] + out,
        }

    def _step_signals_failure(
        self,
        step: WorkflowStep,
        result: AgentResult,
        context: TaskContext,
    ) -> bool:
        """
        Returns True if a completed step's output indicates the on_fail
        policy should trigger (e.g. QA verdict is FAIL).
        Convention: agents write a boolean artifact key '<role>_passed'.
        """
        passed_key = f"{step.agent_role}_passed"
        if passed_key in result.artifacts:
            return not result.artifacts[passed_key]
        # Fallback: check task_artifacts written by agent
        if passed_key in context.task_artifacts:
            return not context.task_artifacts[passed_key]
        return False

    def _apply_failure(
        self,
        step: WorkflowStep,
        result: AgentResult,
        run: WorkflowRun,
    ) -> None:
        logger.error("Step [%s] FAILED: %s", step.name, result.error)
        run.status = "failed"
        run.error  = f"Step '{step.name}': {result.error}"

    def _eval_condition(
        self,
        condition: Optional[StepCondition],
        context: TaskContext,
    ) -> bool:
        if condition is None:
            return True
        value = context.task_artifacts.get(condition.artifact)
        op    = condition.operator
        if op == "eq":       return value == condition.value
        if op == "neq":      return value != condition.value
        if op == "contains": return condition.value in str(value or "")
        if op == "is_set":   return value is not None
        if op == "not_set":  return value is None
        logger.warning("Unknown condition operator '%s'", op)
        return True
