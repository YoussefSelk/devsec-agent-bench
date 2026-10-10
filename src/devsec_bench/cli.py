"""CLI: explicit failures, persisted partial results, offline by default."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from devsec_bench.benchmarks.loader import discover
from devsec_bench.benchmarks.runner import run_suite
from devsec_bench.evaluation.comparison import compare as compare_runs
from devsec_bench.evaluation.comparison import summary
from devsec_bench.models import AgentConfig, Pricing
from devsec_bench.reporting.exporters import export
from devsec_bench.storage.database import Database

app = typer.Typer(no_args_is_help=True, help="Controlled benchmark of security development agents.")
Home = Annotated[Path, typer.Option(help="History and report directory")]


def fail(exc: Exception) -> None:
    typer.echo(f"Error: {exc}", err=True)
    raise typer.Exit(2)


@app.command()
def init(home: Home = Path(".bench")) -> None:
    """Initialize local SQLite history (packaged fixtures need no copying)."""
    Database(home / "history.db")
    typer.echo(f"Initialized {home.resolve()}")


@app.command("list")
def list_scenarios() -> None:
    """List packaged, authorized scenarios."""
    for scenario in discover():
        typer.echo(f"{scenario.id}  {scenario.difficulty:6}  {scenario.name}")


@app.command()
def validate() -> None:
    """Validate all definitions, repositories and ground-truth locations."""
    try:
        typer.echo(f"Validated {len(discover())} scenarios")
    except (ValueError, OSError) as exc:
        fail(exc)


@app.command()
def run(
    agent: str = "reference", model: str | None = None, provider: str = "openai",
    scenario: str | None = None, repetitions: int = 1, concurrency: int = 1,
    seed: int = 0, max_iterations: int = 20, timeout: float = 30,
    request_timeout: float = 20, max_cost: float | None = None,
    pricing_file: Path | None = None, home: Home = Path(".bench"),
    isolation: str = "local",
) -> None:
    """Execute source analysis; non-passing runs exit 1, invalid configuration exits 2."""
    try:
        prices = json.loads(pricing_file.read_text()) if pricing_file else {}
        pricing = Pricing.model_validate(prices[model]) if model in prices else None
        config = AgentConfig.model_validate(dict(agent=agent, model=model, provider=provider, seed=seed, max_iterations=max_iterations, timeout=timeout, request_timeout=request_timeout, max_cost=max_cost, pricing=pricing))
        if isolation == "docker":
            from devsec_bench.isolation import docker_run

            if agent != "reference" or pricing_file or max_cost is not None:
                raise ValueError("Restricted Docker mode supports offline reference runs only")
            command = ["run", "--agent", "reference", "--repetitions", str(repetitions), "--concurrency", str(concurrency), "--seed", str(seed), "--max-iterations", str(max_iterations), "--timeout", str(timeout)]
            if scenario:
                command += ["--scenario", scenario]
            raise typer.Exit(docker_run(home, command, timeout * max(1, repetitions) * 8 + 30))
        if isolation != "local":
            raise ValueError("Isolation must be local or docker")
        scenarios = [s for s in discover() if scenario is None or s.id == scenario]
        if not scenarios:
            raise ValueError("Unknown scenario")
        database = Database(home / "history.db")
        result = run_suite(scenarios, config, repetitions, concurrency, database.save)
        export(result, home / "reports")
        stats = summary(result)
        typer.echo(f'Run {result.id} | {agent} | {stats["passed"]}/{stats["scenarios"]} passed | policy violations {stats["policy_violations"]}')
        for item in result.results:
            typer.echo(f'{item.scenario} {"PASS" if item.metrics.passed else "FAIL"} precision={item.metrics.precision:.2f} recall={item.metrics.recall:.2f} tools={len(item.events)} duration={item.duration:.3f}s status={item.output.status}')
        typer.echo(f'Tokens: {stats["total_tokens"] if stats["total_tokens"] is not None else "unavailable"} | USD: {stats["estimated_cost"] if stats["estimated_cost"] is not None else "unavailable"}')
        if result.interrupted:
            raise typer.Exit(130)
        if not all(r.metrics.passed for r in result.results):
            raise typer.Exit(1)
    except (ValueError, OSError, ValidationError) as exc:
        fail(exc)


@app.command()
def report(run_id: str | None = None, latest: bool = False, home: Home = Path(".bench")) -> None:
    """Regenerate JSON, CSV, HTML and JUnit from stored history."""
    try:
        database = Database(home / "history.db")
        if not latest and not run_id:
            raise ValueError("Supply RUN_ID or --latest")
        result = database.latest() if latest else database.get(str(run_id))
        for kind, path in export(result, home / "reports").items():
            typer.echo(f"{kind}: {path.resolve()}")
    except (ValueError, OSError) as exc:
        fail(exc)


@app.command()
def compare(first: str, second: str, home: Home = Path(".bench")) -> None:
    """Compare two stored run IDs (second minus first)."""
    try:
        database = Database(home / "history.db")
        typer.echo(json.dumps(compare_runs(database.get(first), database.get(second)), indent=2))
    except ValueError as exc:
        fail(exc)


@app.command()
def dashboard(home: Home = Path(".bench"), port: int = 8501) -> None:
    """Launch the Streamlit dashboard with the chosen history path."""
    import os

    environment = dict(os.environ, DEVSEC_BENCH_HOME=str(home.resolve()))
    script = Path(__file__).parent / "dashboard" / "app.py"
    raise typer.Exit(subprocess.call([sys.executable, "-m", "streamlit", "run", str(script), "--server.port", str(port), "--server.address", "127.0.0.1", "--browser.gatherUsageStats", "false"], env=environment))


if __name__ == "__main__":
    app()
