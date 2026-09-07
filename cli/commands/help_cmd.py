"""
agentiq help — formatted command reference with roadmap.
"""
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

app    = typer.Typer()
console = Console()


@app.callback(invoke_without_command=True)
def help_cmd():
    """Show full command reference and roadmap."""

    console.print(Panel(
        "[bold cyan]Agentic Factory[/bold cyan] — AI agent team orchestration",
        box=box.ROUNDED,
        expand=False,
    ))
    console.print()

    # ── Setup ──────────────────────────────────────────────────────────────
    _section("Setup")
    t = _table()
    t.add_row("doctor",   "",                         "Verificar entorno, config y dependencias")
    t.add_row("init",     "",                         "Crear [dim].agentiq/[/dim] en un proyecto nuevo")
    t.add_row("validate", "[dim]--team --workflow[/dim]", "Validar YAML de team y workflow")
    console.print(t)
    console.print()

    # ── Ejecución ──────────────────────────────────────────────────────────
    _section("Ejecución")
    t = _table()
    t.add_row("run", "[dim]--issue owner/repo#N[/dim]", "Procesar un GitHub Issue")
    t.add_row("run", "[dim]--input \"texto\"[/dim]",     "Tarea desde texto libre")
    t.add_row("run", "[dim]--workflow analysis_only[/dim]", "Seleccionar workflow")
    t.add_row("run", "[dim]--async[/dim]",              "No esperar resultado (retorna task_id)")
    t.add_row("status", "[dim]<task_id>[/dim]",         "Consultar estado de una tarea")
    t.add_row("logs",   "",                             "Ver logs en tiempo real")
    console.print(t)
    console.print()

    # ── Recursos ───────────────────────────────────────────────────────────
    _section("Recursos")
    t = _table()
    t.add_row("team list",     "", "Listar teams disponibles")
    t.add_row("workflow list", "", "Listar workflows disponibles")
    t.add_row("profile list",  "", "Listar profiles disponibles")
    console.print(t)
    console.print()

    # ── Roadmap ────────────────────────────────────────────────────────────
    _section("Próximamente", color="dim")
    t = _table(dim=True)
    t.add_row("start",          "",                         "Levantar orquestador + Redis")
    t.add_row("stop",           "",                         "Detener el stack")
    t.add_row("project list",   "",                         "Listar proyectos con .agentiq/")
    t.add_row("project add",    "[dim]<dir>[/dim]",         "Registrar proyecto existente")
    t.add_row("run",            "[dim]--watch[/dim]",       "Progreso en tiempo real durante ejecución")
    t.add_row("team create",    "",                         "Crear team desde wizard")
    t.add_row("profile edit",   "[dim]<name>[/dim]",        "Editar profile con $EDITOR")
    t.add_row("workflow create","",                         "Crear workflow desde template")
    console.print(t)
    console.print()


def _section(title: str, color: str = "bold white"):
    console.print(f"[{color}]{title}[/{color}]")


def _table(dim: bool = False) -> Table:
    t = Table(box=None, show_header=False, padding=(0, 2))
    style = "dim" if dim else ""
    t.add_column("command", style=f"cyan {style}".strip(), min_width=18)
    t.add_column("flags",   style=style, min_width=28)
    t.add_column("desc",    style=style)
    return t
