"""
agentic team list / agentic workflow list / agentic profile list
"""
from __future__ import annotations
import typer

team_app     = typer.Typer(help="Team commands",     no_args_is_help=True)
workflow_app = typer.Typer(help="Workflow commands",  no_args_is_help=True)
profile_app  = typer.Typer(help="Profile commands",   no_args_is_help=True)


# ── team list ─────────────────────────────────────────────────────────────

@team_app.command("list")
def team_list() -> None:
    """List available teams."""
    _list_items("teams", ".yaml", _describe_team)


# ── workflow list ──────────────────────────────────────────────────────────

@workflow_app.command("list")
def workflow_list() -> None:
    """List available workflows."""
    _list_items("workflows", ".yaml", _describe_workflow)


# ── profile list ───────────────────────────────────────────────────────────

@profile_app.command("list")
def profile_list() -> None:
    """List available profiles."""
    _list_items("profiles", ".md", _describe_profile)


# ── Shared helpers ─────────────────────────────────────────────────────────

def _list_items(
    sub: str,
    ext: str,
    describe_fn: "callable",
) -> None:
    import os
    from pathlib import Path
    from rich import print as rprint
    from rich.table import Table
    from rich.console import Console

    from cli.commands.doctor import _factory_dir, _load_dotenv
    _load_dotenv()

    factory_dir = _factory_dir(sub)
    items: dict[str, Path] = {}  # name -> path

    # Factory items
    for p in sorted(factory_dir.glob(f"*{ext}")):
        items[p.stem] = p

    # Project items (override / supplement)
    project_dir = os.environ.get("AGENTIC_PROJECT_DIR")
    if project_dir:
        proj_path = Path(project_dir) / ".agentiq" / sub
        if proj_path.exists():
            for p in sorted(proj_path.glob(f"*{ext}")):
                items[p.stem + " [project]"] = p

    if not items:
        rprint(f"[yellow]No {sub} found in {factory_dir}[/yellow]")
        return

    console = Console()
    table = Table(show_header=True, header_style="bold")
    table.add_column("Name")
    table.add_column("Description")

    for name, path in sorted(items.items()):
        desc = describe_fn(path)
        tag = " [dim](project)[/dim]" if "[project]" in name else ""
        clean_name = name.replace(" [project]", "")
        table.add_row(f"{clean_name}{tag}", desc)

    console.print(table)


def _describe_team(path: "Path") -> str:
    try:
        import yaml
        with open(path) as f:
            data = yaml.safe_load(f)
        desc = ""
        team_block = data.get("team", {})
        if isinstance(team_block, dict):
            desc = team_block.get("description", "")
        if not desc:
            desc = data.get("description", "")
        agents = data.get("agents", [])
        roles = [a.get("role", "?") for a in agents if isinstance(a, dict)]
        detail = f"{', '.join(roles)}" if roles else ""
        return f"{desc}  [dim]{detail}[/dim]" if desc else detail
    except Exception:
        return "[dim]—[/dim]"


def _describe_workflow(path: "Path") -> str:
    try:
        import yaml
        with open(path) as f:
            data = yaml.safe_load(f)
        steps = data.get("steps", [])
        names = [s.get("name", "?") for s in steps if isinstance(s, dict)]
        return f"[dim]{len(names)} steps: {', '.join(names)}[/dim]" if names else "—"
    except Exception:
        return "[dim]—[/dim]"


def _describe_profile(path: "Path") -> str:
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("#"):
                    return line.lstrip("#").strip()
                if line:
                    snippet = line[:80]
                    return f"[dim]{snippet}[/dim]"
        return "[dim]—[/dim]"
    except Exception:
        return "[dim]—[/dim]"
