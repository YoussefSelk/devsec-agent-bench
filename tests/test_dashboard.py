from pathlib import Path

from streamlit.testing.v1 import AppTest

from devsec_bench.benchmarks.loader import discover
from devsec_bench.benchmarks.runner import run_suite
from devsec_bench.models import AgentConfig, Run
from devsec_bench.storage.database import Database


def test_dashboard_reads_actual_history(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DEVSEC_BENCH_HOME", str(tmp_path))
    database = Database(tmp_path / "history.db")
    database.save(run_suite(discover(), AgentConfig()))
    app = Path(__file__).parents[1] / "src/devsec_bench/dashboard/app.py"
    test = AppTest.from_file(str(app)).run(timeout=30)
    assert not test.exception
    assert test.metric[0].value == "1"
    for page in ["Benchmark Results", "Agent Comparison", "Execution Traces", "Reports"]:
        test.radio[0].set_value(page).run(timeout=30)
        assert not test.exception


def test_dashboard_empty_history(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DEVSEC_BENCH_HOME", str(tmp_path))
    test = AppTest.from_file(
        str(Path(__file__).parents[1] / "src/devsec_bench/dashboard/app.py")
    ).run(timeout=30)
    assert not test.exception
    assert test.info


def test_dashboard_incomplete_initial_snapshot(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DEVSEC_BENCH_HOME", str(tmp_path))
    Database(tmp_path / "history.db").save(Run(id="pending", config=AgentConfig()))
    test = AppTest.from_file(
        str(Path(__file__).parents[1] / "src/devsec_bench/dashboard/app.py")
    ).run(timeout=30)
    for page in ["Benchmark Results", "Agent Comparison", "Execution Traces", "Reports"]:
        test.radio[0].set_value(page).run(timeout=30)
        assert not test.exception
