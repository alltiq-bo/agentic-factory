"""
agentic doctor — health check of the environment.
"""
from __future__ import annotations
import typer

app = typer.Typer(invoke_without_command=True)


@app.callback(invoke_without_command=True)
def doctor(ctx: typer.Context) -> None:
    """Health check of the environment."""
    if ctx.invoked_subcommand is not None:
        return
    _run_doctor()


def _run_doctor() -> None:
    import os
    import shutil
    import subprocess
    import sys
    from pathlib import Path
    from rich.console import Console
    from rich import print as rprint

    console = Console()
    issues: int = 0

    def ok(msg: str) -> None:
        rprint(f"  [green]✓[/green] {msg}")

    def fail(msg: str) -> None:
        nonlocal issues
        issues += 1
        rprint(f"  [red]✗[/red] {msg}")

    def warn(msg: str) -> None:
        rprint(f"  [yellow]⚠[/yellow] {msg}")

    # ── Load .env early ────────────────────────────────────────────────────
    _load_dotenv()

    # ─────────────────────────────────────────────────────────────────────
    rprint("\n[bold]Environment[/bold]")

    # Python version
    vi = sys.version_info
    if vi >= (3, 10):
        ok(f"Python {vi.major}.{vi.minor}.{vi.micro}")
    else:
        fail(f"Python {vi.major}.{vi.minor}.{vi.micro} — need >= 3.10")

    # CLAUDE_BIN
    claude_bin = os.environ.get("CLAUDE_BIN") or shutil.which("claude") or "claude"
    if os.path.isfile(claude_bin) and os.access(claude_bin, os.X_OK):
        ok(f"CLAUDE_BIN: {claude_bin}")
    else:
        found = shutil.which(claude_bin)
        if found:
            ok(f"CLAUDE_BIN: {found} (via PATH)")
        else:
            fail(f"CLAUDE_BIN not found or not executable: {claude_bin}")

    # CLAUDE_CONFIG_DIR
    config_dir = os.environ.get("CLAUDE_CONFIG_DIR")
    if config_dir:
        if Path(config_dir).exists():
            ok(f"CLAUDE_CONFIG_DIR: {config_dir}")
        else:
            fail(f"CLAUDE_CONFIG_DIR set but does not exist: {config_dir}")
    else:
        warn("CLAUDE_CONFIG_DIR not set")

    # Redis
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    try:
        result = subprocess.run(
            ["redis-cli", "-u", redis_url, "ping"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and "PONG" in result.stdout.upper():
            ok(f"Redis reachable at {redis_url}")
        else:
            fail(f"Redis not responding at {redis_url}")
    except FileNotFoundError:
        fail("redis-cli not found — install Redis tools")
    except subprocess.TimeoutExpired:
        fail(f"Redis timeout at {redis_url}")

    # Docker (optional)
    docker_path = shutil.which("docker")
    if docker_path:
        try:
            r = subprocess.run(["docker", "info"], capture_output=True, timeout=5)
            if r.returncode == 0:
                ok("Docker available")
            else:
                warn("Docker installed but daemon not running")
        except subprocess.TimeoutExpired:
            warn("Docker timeout")
    else:
        warn("Docker not available (optional)")

    # ─────────────────────────────────────────────────────────────────────
    rprint("\n[bold]Configuration[/bold]")

    # .env file
    env_path = _find_dotenv()
    if env_path:
        ok(f".env found: {env_path}")
    else:
        fail(".env not found in cwd or parents")

    # GH_TOKEN
    if os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN"):
        ok("GH_TOKEN set")
    else:
        fail("GH_TOKEN not set")

    # TEAM_CONFIG
    team_config = os.environ.get("TEAM_CONFIG")
    if team_config:
        ok(f"TEAM_CONFIG={team_config}")
    else:
        fail("TEAM_CONFIG not set")

    # Team YAML
    if team_config:
        team_path = _resolve_yaml("teams", team_config)
        if team_path and team_path.exists():
            try:
                import yaml
                with open(team_path) as f:
                    team_data = yaml.safe_load(f)
                ok(f"Team YAML parseable: {team_path.name}")
            except Exception as e:
                fail(f"Team YAML parse error: {e}")
                team_data = None
        else:
            fail(f"Team YAML not found: teams/{team_config}.yaml")
            team_data = None
    else:
        team_data = None

    # Workflow YAML
    workflow_name = os.environ.get("WORKFLOW_CONFIG", "analysis_only")
    if team_data:
        workflow_ref = team_data.get("workflow")
        if isinstance(workflow_ref, str):
            workflow_name = workflow_ref
    wf_path = _resolve_yaml("workflows", workflow_name)
    if wf_path and wf_path.exists():
        try:
            import yaml
            with open(wf_path) as f:
                yaml.safe_load(f)
            ok(f"Workflow YAML parseable: {wf_path.name}")
        except Exception as e:
            fail(f"Workflow YAML parse error: {e}")
    else:
        fail(f"Workflow YAML not found: workflows/{workflow_name}.yaml")

    # Profiles referenced in team YAML
    if team_data:
        profiles_dir = _factory_dir("profiles")
        agents = team_data.get("agents", [])
        for agent in agents:
            profile = agent.get("profile")
            if profile:
                prof_path = profiles_dir / f"{profile}.md"
                if prof_path.exists():
                    ok(f"Profile exists: {profile}.md")
                else:
                    fail(f"Profile missing: {profile}.md")

    # ─────────────────────────────────────────────────────────────────────
    rprint("\n[bold]Orchestrator[/bold]")

    try:
        import httpx
        resp = httpx.get("http://localhost:8000/health", timeout=3)
        if resp.status_code == 200:
            ok("Orchestrator health check passed")
        else:
            fail(f"Orchestrator returned HTTP {resp.status_code}")
    except Exception:
        fail("Orchestrator not reachable at http://localhost:8000")

    # ── Summary ────────────────────────────────────────────────────────────
    rprint("")
    if issues == 0:
        rprint("[bold green]✅ Ready[/bold green]")
    else:
        rprint(f"[bold red]❌ {issues} issue{'s' if issues != 1 else ''} found[/bold red]")

    if issues:
        raise typer.Exit(code=1)


def _load_dotenv() -> None:
    """Load .env file into os.environ if not already set."""
    env_path = _find_dotenv()
    if not env_path:
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path, override=False)
        return
    except ImportError:
        pass
    # Manual parse fallback
    import os
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val


def _find_dotenv() -> "Path | None":
    from pathlib import Path
    cwd = Path.cwd()
    for p in [cwd, *cwd.parents]:
        candidate = p / ".env"
        if candidate.exists():
            return candidate
    return None


def _factory_dir(sub: str) -> "Path":
    from pathlib import Path
    # __file__ = .../agentic_factory/cli/commands/doctor.py
    # parents[2] = .../agentic_factory
    return Path(__file__).parents[2] / sub


def _resolve_yaml(sub: str, name: str) -> "Path | None":
    import os
    from pathlib import Path
    # Check project dir first
    project_dir = os.environ.get("AGENTIC_PROJECT_DIR")
    if project_dir:
        candidate = Path(project_dir) / ".agentic" / f"{name}.yaml"
        if candidate.exists():
            return candidate
    return _factory_dir(sub) / f"{name}.yaml"
