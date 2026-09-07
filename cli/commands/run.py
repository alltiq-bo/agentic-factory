"""
agentic run — submit a task to the running orchestrator.
"""
from __future__ import annotations
from typing import Optional
import typer

app = typer.Typer(invoke_without_command=True)


@app.callback(invoke_without_command=True)
def run(
    ctx: typer.Context,
    issue: Optional[str] = typer.Option(
        None, "--issue", "-i",
        help="GitHub issue ref: owner/repo#N",
    ),
    input_text: Optional[str] = typer.Option(
        None, "--input", "-t",
        help="Free text task input",
    ),
    workflow: str = typer.Option(
        "analysis_only", "--workflow", "-w",
        help="Workflow override",
    ),
    project_id: str = typer.Option(
        "default", "--project-id", "-p",
        help="Project ID",
    ),
    sync: bool = typer.Option(
        True, "--sync/--async",
        help="Wait for result (sync) or return task_id immediately (async)",
    ),
    url: str = typer.Option(
        "http://localhost:8000", "--url",
        help="Orchestrator URL",
    ),
) -> None:
    """Submit a task to the running orchestrator."""
    if ctx.invoked_subcommand is not None:
        return
    _run_task(issue, input_text, workflow, project_id, sync, url)


def _run_task(
    issue: Optional[str],
    input_text: Optional[str],
    workflow: str,
    project_id: str,
    sync: bool,
    url: str,
) -> None:
    import json
    import httpx
    from rich import print as rprint

    from cli.commands.doctor import _load_dotenv
    _load_dotenv()

    if not issue and not input_text:
        rprint("[red]Provide --issue or --input[/red]")
        raise typer.Exit(code=1)

    # Build payload
    payload: dict = {
        "workflow": workflow,
        "project_id": project_id,
    }

    if issue:
        parsed = _parse_issue_ref(issue)
        if not parsed:
            rprint(f"[red]Invalid issue format '{issue}' — expected owner/repo#N[/red]")
            raise typer.Exit(code=1)
        payload["issue"] = parsed
        rprint(f"Submitting issue [cyan]{issue}[/cyan] → workflow [cyan]{workflow}[/cyan]")
    else:
        payload["input"] = input_text
        preview = (input_text[:60] + "...") if len(input_text) > 60 else input_text
        rprint(f"Submitting input: [cyan]{preview}[/cyan] → workflow [cyan]{workflow}[/cyan]")

    endpoint = f"{url.rstrip('/')}/tasks{'sync' and '/sync' or ''}"
    if not sync:
        endpoint = f"{url.rstrip('/')}/tasks"

    try:
        with httpx.Client(timeout=300 if sync else 10) as client:
            resp = client.post(endpoint, json=payload)

        if resp.status_code in (200, 201, 202):
            data = resp.json()
            _print_result(data, sync)
        else:
            rprint(f"[red]HTTP {resp.status_code}:[/red] {resp.text}")
            raise typer.Exit(code=1)

    except httpx.ConnectError:
        rprint(f"[red]Cannot connect to orchestrator at {url}[/red]")
        rprint("Is the orchestrator running? Try: [cyan]uvicorn orchestrator.api.main:app[/cyan]")
        raise typer.Exit(code=1)
    except httpx.TimeoutException:
        rprint("[yellow]Request timed out. The task may still be running.[/yellow]")
        raise typer.Exit(code=1)


def _parse_issue_ref(ref: str) -> "dict | None":
    """Parse 'owner/repo#N' into {'repo': 'owner/repo', 'number': N}."""
    if "#" not in ref:
        return None
    repo_part, _, number_part = ref.rpartition("#")
    if not repo_part or not number_part:
        return None
    try:
        return {"repo": repo_part, "number": int(number_part)}
    except ValueError:
        return None


def _print_result(data: dict, sync: bool) -> None:
    from rich import print as rprint
    from rich.table import Table
    from rich.console import Console

    console = Console()

    if not sync:
        task_id = data.get("task_id") or data.get("id") or "?"
        rprint(f"\n[green]Task submitted[/green] — ID: [bold]{task_id}[/bold]")
        rprint(f"Check status: [cyan]agentic status {task_id}[/cyan]")
        return

    # Sync result
    task_id = data.get("task_id") or data.get("id") or "?"
    status = data.get("status", "?")
    rprint(f"\n[bold]Task:[/bold] {task_id}")
    rprint(f"[bold]Status:[/bold] {_status_colored(status)}")

    if "error" in data and data["error"]:
        rprint(f"[bold red]Error:[/bold red] {data['error']}")

    artifacts = data.get("artifacts") or data.get("output") or {}
    if artifacts and isinstance(artifacts, dict):
        rprint(f"\n[bold]Artifacts:[/bold]")
        for key, val in artifacts.items():
            if isinstance(val, str) and len(val) > 200:
                val = val[:200] + "..."
            rprint(f"  [cyan]{key}[/cyan]: {val}")


def _status_colored(status: str) -> str:
    colors = {
        "completed": "green",
        "failed": "red",
        "running": "yellow",
        "pending": "dim",
    }
    color = colors.get(status.lower(), "white")
    return f"[{color}]{status}[/{color}]"
