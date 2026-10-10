import csv
import json
from pathlib import Path
from xml.etree import ElementTree

from typer.testing import CliRunner

from devsec_bench.benchmarks.loader import discover
from devsec_bench.benchmarks.runner import run_suite
from devsec_bench.cli import app
from devsec_bench.evaluation.comparison import compare
from devsec_bench.models import AgentConfig
from devsec_bench.reporting.exporters import export
from devsec_bench.storage.database import Database


def test_database_roundtrip_and_sanitized_reports(tmp_path: Path):
    run = run_suite(discover()[:2], AgentConfig())
    run.results[0].output.findings[0].explanation = 'api_key=sk-THIS_IS_A_PRIVATE_TOKEN'
    database = Database(tmp_path / "history.db")
    database.save(run)
    loaded = database.get(run.id)
    assert loaded.id == run.id
    assert len(loaded.results) == 2
    assert "PRIVATE_TOKEN" not in loaded.model_dump_json()
    assert database.latest().id == run.id
    assert database.list_runs()[0].id == run.id
    paths = export(loaded, tmp_path / "reports")
    assert json.loads(paths["json"].read_text())["id"] == run.id
    assert len(list(csv.DictReader(paths["csv"].open()))) == 2
    assert ElementTree.parse(paths["junit"]).getroot().attrib["tests"] == "2"
    assert "&lt;" not in paths["html"].read_text() or "<script>" not in paths["html"].read_text()
    assert "PRIVATE_TOKEN" not in paths["html"].read_text()


def test_comparison_uses_measured_runs():
    first = run_suite(discover()[:1], AgentConfig())
    second = run_suite(discover()[:1], AgentConfig(max_iterations=1))
    result = compare(first, second)
    assert result["success_rate_delta"] == -1.0
    assert result["runs"][0]["estimated_cost"] is None


def test_cli_end_to_end(tmp_path: Path):
    runner = CliRunner()
    assert runner.invoke(app, ["init", "--home", str(tmp_path)]).exit_code == 0
    assert runner.invoke(app, ["list"]).exit_code == 0
    assert runner.invoke(app, ["validate"]).exit_code == 0
    result = runner.invoke(app, ["run", "--agent", "reference", "--home", str(tmp_path), "--concurrency", "2"])
    assert result.exit_code == 0, result.output
    assert "8/8" in result.output
    report = runner.invoke(app, ["report", "--latest", "--home", str(tmp_path)])
    assert report.exit_code == 0, report.output
    db = Database(tmp_path / "history.db")
    run_id = db.latest().id
    assert runner.invoke(app, ["compare", run_id, run_id, "--home", str(tmp_path)]).exit_code == 0
    assert runner.invoke(app, ["run", "--scenario", "unknown", "--home", str(tmp_path)]).exit_code != 0


def test_missing_credentials_clean_failure(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = CliRunner().invoke(app, ["run", "--agent", "llm", "--model", "caller-model", "--home", str(tmp_path)])
    assert result.exit_code != 0
    assert "OPENAI_API_KEY" in result.output
    assert "Traceback" not in result.output
