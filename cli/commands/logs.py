"""
agentic logs — tail /tmp/orchestrator.log.
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional
import typer

app = typer.Typer(invoke_without_command=True)

_DEFAULT_LOG = "/tmp/orchestrator.log"


@app.callback(invoke_without_command=True)
def logs(
    ctx: typer.Context,
    log_file: Optional[str] = typer.Option(
        None, "--file", "-f",
        help=f"Log file path (default: {_DEFAULT_LOG})",
    ),
    lines: int = typer.Option(
        50, "--lines", "-n",
        help="Number of initial lines to show",
    ),
) -> None:
    """Tail the orchestrator log file."""
    if ctx.invoked_subcommand is not None:
        return
    _run_logs(log_file or _DEFAULT_LOG, lines)


def _run_logs(log_file: str, lines: int) -> None:
    import subprocess
    from rich import print as rprint

    path = Path(log_file)
    if not path.exists():
        rprint(f"[yellow]Log file not found:[/yellow] {log_file}")
        rprint("The orchestrator may not be running yet.")
        raise typer.Exit(code=1)

    rprint(f"[dim]Tailing {log_file} (Ctrl+C to stop)...[/dim]\n")
    try:
        subprocess.run(["tail", f"-n{lines}", "-f", log_file])
    except KeyboardInterrupt:
        pass
    except FileNotFoundError:
        rprint("[red]'tail' command not found[/red]")
        raise typer.Exit(code=1)
