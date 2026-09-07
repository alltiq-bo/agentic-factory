"""
agentic validate — validate team/workflow YAML config.
"""
from __future__ import annotations
from typing import Optional
import typer

app = typer.Typer(invoke_without_command=True)


@app.callback(invoke_without_command=True)
def validate(
    ctx: typer.Context,
    team: Optional[str] = typer.Option(None, "--team", "-t",
                                       help="Team YAML name (default: $TEAM_CONFIG)"),
    workflow: Optional[str] = typer.Option(None, "--workflow", "-w",
                                           help="Workflow YAML name"),
) -> None:
    """Validate team and workflow YAML config files."""
    if ctx.invoked_subcommand is not None:
        return
    _run_validate(team, workflow)


def _run_validate(team_name: Optional[str], workflow_name: Optional[str]) -> None:
    import os
    import yaml
    from pathlib import Path
    from rich import print as rprint

    from cli.commands.doctor import _load_dotenv, _factory_dir, _resolve_yaml
    _load_dotenv()

    issues: int = 0

    def ok(msg: str) -> None:
        rprint(f"  [green]✓[/green] {msg}")

    def fail(msg: str) -> None:
        nonlocal issues
        issues += 1
        rprint(f"  [red]✗[/red] {msg}")

    def warn(msg: str) -> None:
        rprint(f"  [yellow]⚠[/yellow] {msg}")

    team_name = team_name or os.environ.get("TEAM_CONFIG", "")
    if not team_name:
        rprint("[red]No team specified. Use --team or set TEAM_CONFIG.[/red]")
        raise typer.Exit(code=1)

    # ── Team YAML ──────────────────────────────────────────────────────────
    rprint(f"\n[bold]Team: {team_name}[/bold]")
    team_path = _resolve_yaml("teams", team_name)

    if not team_path or not team_path.exists():
        fail(f"Team YAML not found: {team_path}")
        raise typer.Exit(code=1)

    try:
        with open(team_path) as f:
            team_data = yaml.safe_load(f)
        ok(f"Team YAML parses OK: {team_path.name}")
    except Exception as e:
        fail(f"Team YAML parse error: {e}")
        raise typer.Exit(code=1)

    agents_in_team: set[str] = set()
    for agent in team_data.get("agents", []):
        role = agent.get("role")
        if role:
            agents_in_team.add(role)

    if agents_in_team:
        ok(f"Agents defined: {', '.join(sorted(agents_in_team))}")
    else:
        fail("No agents defined in team YAML")

    # ── Profiles referenced in team ────────────────────────────────────────
    rprint(f"\n[bold]Profiles[/bold]")
    profiles_dir = _factory_dir("profiles")
    project_dir = os.environ.get("AGENTIC_PROJECT_DIR")
    project_profiles_dir = Path(project_dir) / ".agentic" / "profiles" if project_dir else None

    for agent in team_data.get("agents", []):
        profile = agent.get("profile")
        role = agent.get("role", "?")
        if profile:
            found = False
            if project_profiles_dir:
                p = project_profiles_dir / f"{profile}.md"
                if p.exists():
                    found = True
            if not found:
                p = profiles_dir / f"{profile}.md"
                if p.exists():
                    found = True
            if found:
                ok(f"Profile {profile}.md (role: {role})")
            else:
                fail(f"Profile missing: {profile}.md (role: {role})")

    # ── Workflow YAML ──────────────────────────────────────────────────────
    if not workflow_name:
        wf_ref = team_data.get("workflow")
        if isinstance(wf_ref, str):
            workflow_name = wf_ref
        elif isinstance(wf_ref, dict):
            workflow_name = wf_ref.get("name", "")
        else:
            workflow_name = os.environ.get("WORKFLOW_CONFIG", "analysis_only")

    rprint(f"\n[bold]Workflow: {workflow_name}[/bold]")
    wf_path = _resolve_yaml("workflows", workflow_name)

    if not wf_path or not wf_path.exists():
        fail(f"Workflow YAML not found: {wf_path}")
        raise typer.Exit(code=1)

    try:
        with open(wf_path) as f:
            wf_data = yaml.safe_load(f)
        ok(f"Workflow YAML parses OK: {wf_path.name}")
    except Exception as e:
        fail(f"Workflow YAML parse error: {e}")
        raise typer.Exit(code=1)

    steps = wf_data.get("steps", [])
    step_names: set[str] = {s["name"] for s in steps if "name" in s}

    if step_names:
        ok(f"Steps defined: {', '.join(sorted(step_names))}")
    else:
        fail("No steps defined in workflow YAML")

    # ── agent_role in workflow steps exists in team agents ─────────────────
    rprint(f"\n[bold]Cross-checks[/bold]")
    for step in steps:
        step_name = step.get("name", "?")
        agent_role = step.get("agent_role")
        if agent_role:
            if agent_role in agents_in_team:
                ok(f"Step '{step_name}' agent_role '{agent_role}' found in team")
            else:
                fail(f"Step '{step_name}' agent_role '{agent_role}' NOT in team agents: {sorted(agents_in_team)}")

    # depends_on references
    for step in steps:
        step_name = step.get("name", "?")
        for dep in step.get("depends_on", []):
            if dep in step_names:
                ok(f"Step '{step_name}' depends_on '{dep}' valid")
            else:
                fail(f"Step '{step_name}' depends_on '{dep}' — step not found")

    # ── Summary ────────────────────────────────────────────────────────────
    rprint("")
    if issues == 0:
        rprint("[bold green]✅ Validation passed[/bold green]")
    else:
        rprint(f"[bold red]❌ {issues} issue{'s' if issues != 1 else ''} found[/bold red]")

    if issues:
        raise typer.Exit(code=1)
