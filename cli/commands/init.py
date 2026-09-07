"""
agentic init — interactive scaffolding of .agentiq/ in a target project dir.
"""
from __future__ import annotations
import typer

app = typer.Typer(invoke_without_command=True)

_LLM_PROVIDERS = ["claude_code", "anthropic", "openai", "ollama"]


@app.callback(invoke_without_command=True)
def init(ctx: typer.Context) -> None:
    """Interactive scaffolding of .agentiq/ in a project directory."""
    if ctx.invoked_subcommand is not None:
        return
    _run_init()


def _run_init() -> None:
    import os
    import shutil
    from pathlib import Path
    from rich import print as rprint

    from cli.commands.doctor import _factory_dir

    rprint("\n[bold]Agentic Factory — Project Init Wizard[/bold]\n")

    # 1. Target directory
    default_dir = str(Path.cwd())
    target_str = typer.prompt("Target directory", default=default_dir)
    target_dir = Path(target_str).expanduser().resolve()

    if not target_dir.exists():
        if typer.confirm(f"Directory {target_dir} does not exist. Create it?", default=True):
            target_dir.mkdir(parents=True)
        else:
            raise typer.Abort()

    agentic_dir = target_dir / ".agentiq"
    if agentic_dir.exists():
        if not typer.confirm(f".agentiq/ already exists in {target_dir}. Overwrite?", default=False):
            raise typer.Abort()

    # 2. Project name
    project_name = typer.prompt("Project name", default=target_dir.name)

    # 3. GitHub repo
    github_repo = typer.prompt("GitHub repo (owner/repo, optional)", default="")

    # 4. Team selection
    teams_dir = _factory_dir("teams")
    available_teams = [p.stem for p in sorted(teams_dir.glob("*.yaml"))]
    rprint("\n[bold]Available teams:[/bold]")
    for i, t in enumerate(available_teams, 1):
        rprint(f"  {i}. {t}")
    rprint(f"  {len(available_teams) + 1}. custom")

    team_choice = typer.prompt(
        "Select team (number or name)",
        default="1",
    )
    selected_team: str | None = None
    try:
        idx = int(team_choice)
        if 1 <= idx <= len(available_teams):
            selected_team = available_teams[idx - 1]
        else:
            selected_team = None  # custom
    except ValueError:
        if team_choice in available_teams:
            selected_team = team_choice
        elif team_choice.lower() == "custom":
            selected_team = None
        else:
            rprint(f"[yellow]Team '{team_choice}' not found — using template[/yellow]")
            selected_team = None

    # 5. LLM provider
    rprint("\n[bold]LLM Providers:[/bold]")
    for i, p in enumerate(_LLM_PROVIDERS, 1):
        rprint(f"  {i}. {p}")

    provider_choice = typer.prompt("Select LLM provider (number or name)", default="1")
    selected_provider = _LLM_PROVIDERS[0]
    try:
        idx = int(provider_choice)
        if 1 <= idx <= len(_LLM_PROVIDERS):
            selected_provider = _LLM_PROVIDERS[idx - 1]
    except ValueError:
        if provider_choice in _LLM_PROVIDERS:
            selected_provider = provider_choice

    # 6. CLAUDE_CONFIG_DIR if claude_code
    claude_config_dir = ""
    if selected_provider == "claude_code":
        claude_config_dir = typer.prompt(
            "CLAUDE_CONFIG_DIR (optional)",
            default=os.environ.get("CLAUDE_CONFIG_DIR", ""),
        )

    # ── Create .agentiq/ structure ─────────────────────────────────────────
    rprint(f"\n[bold]Creating .agentiq/ in {target_dir}[/bold]\n")
    agentic_dir.mkdir(parents=True, exist_ok=True)
    (agentic_dir / "profiles").mkdir(exist_ok=True)
    (agentic_dir / "guidelines").mkdir(exist_ok=True)

    created: list[str] = []

    # project.yaml
    _write_project_yaml(agentic_dir, project_name, github_repo)
    created.append(".agentiq/project.yaml")

    # team.yaml
    templates_dir = Path(__file__).parents[1] / "templates"
    if selected_team:
        src_team = teams_dir / f"{selected_team}.yaml"
        dst_team = agentic_dir / "team.yaml"
        shutil.copy2(src_team, dst_team)
        created.append(f".agentiq/team.yaml (from {selected_team})")

        # copy referenced profiles
        import yaml
        with open(src_team) as f:
            team_data = yaml.safe_load(f)
        profiles_dir = _factory_dir("profiles")
        for agent in team_data.get("agents", []):
            profile = agent.get("profile")
            if profile:
                src_prof = profiles_dir / f"{profile}.md"
                if src_prof.exists():
                    shutil.copy2(src_prof, agentic_dir / "profiles" / f"{profile}.md")
                    created.append(f".agentiq/profiles/{profile}.md")
    else:
        shutil.copy2(templates_dir / "team.yaml", agentic_dir / "team.yaml")
        created.append(".agentiq/team.yaml (from template)")

    # workflow.yaml
    shutil.copy2(templates_dir / "workflow.yaml", agentic_dir / "workflow.yaml")
    created.append(".agentiq/workflow.yaml")

    # .env.example
    _write_env_example(agentic_dir, selected_team, selected_provider, claude_config_dir)
    created.append(".agentiq/.env.example")

    # Print summary
    rprint("[bold green]Created:[/bold green]")
    for item in created:
        rprint(f"  [green]✓[/green] {item}")

    rprint(f"\n[bold]Next steps:[/bold]")
    rprint(f"  1. Copy [cyan].agentiq/.env.example[/cyan] to [cyan].env[/cyan] and fill in values")
    rprint(f"  2. Edit [cyan].agentiq/team.yaml[/cyan] to customize your team")
    rprint(f"  3. Run [cyan]agentic validate[/cyan] to check the config")
    rprint(f"  4. Run [cyan]agentic doctor[/cyan] to check the environment")


def _write_project_yaml(agentic_dir: "Path", name: str, repo: str) -> None:
    content = f"""# Agentic Factory — Project Metadata
project:
  name: {name}
  repo: {repo or 'owner/repo'}
  description: ''
"""
    (agentic_dir / "project.yaml").write_text(content)


def _write_env_example(
    agentic_dir: "Path",
    team: "str | None",
    provider: str,
    claude_config_dir: str,
) -> None:
    team_val = team or "default_team"
    lines = [
        "# Agentic Factory environment variables",
        f"TEAM_CONFIG={team_val}",
        "WORKFLOW_CONFIG=analysis_only",
        "",
        "# GitHub",
        "GH_TOKEN=your_github_token",
        "",
        "# Redis",
        "REDIS_URL=redis://localhost:6379",
        "",
        "# LLM",
    ]

    if provider == "claude_code":
        lines += [
            f"CLAUDE_BIN=claude",
            f"CLAUDE_CONFIG_DIR={claude_config_dir or '/path/to/.claude'}",
        ]
    elif provider == "anthropic":
        lines += ["ANTHROPIC_API_KEY=sk-ant-..."]
    elif provider == "openai":
        lines += ["OPENAI_API_KEY=sk-..."]
    elif provider == "ollama":
        lines += ["OLLAMA_BASE_URL=http://localhost:11434"]

    lines += [
        "",
        "# Optional",
        "LOG_LEVEL=INFO",
        "AGENTIC_PROJECT_DIR=.",
    ]

    (agentic_dir / ".env.example").write_text("\n".join(lines) + "\n")
