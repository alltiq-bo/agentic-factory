"""
agentic status <task_id> — check task status.
"""
from __future__ import annotations
import typer

app = typer.Typer(invoke_without_command=True)


@app.callback(invoke_without_command=True)
def status(
    ctx: typer.Context,
    task_id: str = typer.Argument(..., help="Task ID to check"),
    url: str = typer.Option("http://localhost:8000", "--url", help="Orchestrator URL"),
) -> None:
    """Check the status of a submitted task."""
    if ctx.invoked_subcommand is not None:
        return
    _run_status(task_id, url)


def _run_status(task_id: str, url: str) -> None:
    import httpx
    from rich import print as rprint

    from cli.commands.doctor import _load_dotenv
    _load_dotenv()

    endpoint = f"{url.rstrip('/')}/tasks/{task_id}"

    try:
        resp = httpx.get(endpoint, timeout=10)
    except httpx.ConnectError:
        rprint(f"[red]Cannot connect to orchestrator at {url}[/red]")
        raise typer.Exit(code=1)

    if resp.status_code == 404:
        rprint(f"[red]Task not found:[/red] {task_id}")
        raise typer.Exit(code=1)

    if resp.status_code != 200:
        rprint(f"[red]HTTP {resp.status_code}:[/red] {resp.text}")
        raise typer.Exit(code=1)

    data = resp.json()
    _print_status(data)


def _print_status(data: dict) -> None:
    from rich import print as rprint

    task_id    = data.get("task_id") or data.get("id") or "?"
    status     = data.get("status", "?")
    step       = data.get("current_step") or data.get("step", "—")
    qa_cycle   = data.get("qa_cycle", "—")
    error      = data.get("error") or "—"

    status_colors = {
        "completed": "green",
        "failed": "red",
        "running": "yellow",
        "pending": "dim",
    }
    color = status_colors.get(str(status).lower(), "white")

    rprint(f"\n[bold]Task:[/bold]         {task_id}")
    rprint(f"[bold]Status:[/bold]        [{color}]{status}[/{color}]")
    rprint(f"[bold]Current step:[/bold]  {step}")
    rprint(f"[bold]QA cycle:[/bold]      {qa_cycle}")
    rprint(f"[bold]Error:[/bold]         {error}")
