"""
run_local.py — Ejecuta un task directamente sin Docker ni API.
Útil para desarrollo, debugging y entender el flujo.

Uso:
    python run_local.py "Migrar el módulo de autenticación de .NET MVC 5 a .NET 8"
    python run_local.py "Build a REST API for user registration" --team default_team
"""
import asyncio
import argparse
import logging
import os
import sys
from pathlib import Path

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)

async def main():
    parser = argparse.ArgumentParser(description="Run Agentic Factory locally")
    parser.add_argument("input", help="Task description")
    parser.add_argument("--team",       default="dotnet-react-migration")
    parser.add_argument("--project-id", default="local-run")
    args = parser.parse_args()

    from orchestrator.orchestrator import Orchestrator
    from orchestrator.core.state_manager import StateManager
    from knowledge_base.store import KnowledgeBase

    sm  = StateManager()   # in-memory (no Redis needed for local run)
    kb  = KnowledgeBase()  # in-memory

    orch = Orchestrator(
        state_manager  = sm,
        knowledge_base = kb,
        team_name      = args.team,
    )

    print(f"\n{'='*60}")
    print(f"  Team     : {args.team}")
    print(f"  Input    : {args.input[:80]}...")
    print(f"{'='*60}\n")

    run = await orch.run_task(
        input_text = args.input,
        project_id = args.project_id,
    )

    print(f"\n{'='*60}")
    print(f"  Status   : {run.status.upper()}")
    print(f"  QA cycles: {run.qa_cycle}")
    if run.error:
        print(f"  Error    : {run.error}")
    print(f"  Steps run: {list(run.results.keys())}")
    print(f"{'='*60}\n")

    # Print each agent's output summary
    for step_name, result in run.results.items():
        print(f"\n── {step_name} ({result.agent_role}) ─────────────────────")
        print(result.output[:500] + ("..." if len(result.output) > 500 else ""))

    return run


if __name__ == "__main__":
    asyncio.run(main())
