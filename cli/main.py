"""
Agentic Factory CLI — root typer app.
Registers all commands and sub-apps.
"""
import typer

app = typer.Typer(
    name="agentiq",
    help="Agentic Factory — AI agent team orchestration CLI",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

# ── Leaf-command sub-apps ──────────────────────────────────────────────────
from cli.commands.doctor   import app as doctor_app    # noqa: E402
from cli.commands.validate import app as validate_app  # noqa: E402
from cli.commands.init     import app as init_app      # noqa: E402
from cli.commands.run      import app as run_app       # noqa: E402
from cli.commands.status   import app as status_app    # noqa: E402
from cli.commands.logs     import app as logs_app      # noqa: E402
from cli.commands.list_cmd import (                    # noqa: E402
    team_app, workflow_app, profile_app,
)

app.add_typer(doctor_app,   name="doctor",   invoke_without_command=True,
              help="Health check of the environment")
app.add_typer(validate_app, name="validate", invoke_without_command=True,
              help="Validate team/workflow YAML config")
app.add_typer(init_app,     name="init",     invoke_without_command=True,
              help="Interactive scaffolding of .agentic/ in a project dir")
app.add_typer(run_app,      name="run",      invoke_without_command=True,
              help="Submit a task to the running orchestrator")
app.add_typer(status_app,   name="status",   invoke_without_command=True,
              help="Check task status")
app.add_typer(logs_app,     name="logs",     invoke_without_command=True,
              help="Tail /tmp/orchestrator.log")
app.add_typer(team_app,     name="team",     help="Team commands")
app.add_typer(workflow_app, name="workflow", help="Workflow commands")
app.add_typer(profile_app,  name="profile",  help="Profile commands")


if __name__ == "__main__":
    app()
