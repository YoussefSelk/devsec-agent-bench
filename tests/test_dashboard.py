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
    for page in [
        "Benchmark Runs",
        "Scenarios",
        "Agent Comparison",
        "Execution Traces",
        "Reports",
        "Settings",
    ]:
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
    for page in [
        "Benchmark Runs",
        "Scenarios",
        "Agent Comparison",
        "Execution Traces",
        "Reports",
        "Settings",
    ]:
        test.radio[0].set_value(page).run(timeout=30)
        assert not test.exception


def test_dashboard_runs_real_reference_and_refreshes_history(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DEVSEC_BENCH_HOME", str(tmp_path))
    test = AppTest.from_file(
        str(Path(__file__).parents[1] / "src/devsec_bench/dashboard/app.py")
    ).run(timeout=30)
    next(button for button in test.button if button.label == "Start reference run").click().run(
        timeout=30
    )
    assert not test.exception
    run = Database(tmp_path / "history.db").latest()
    assert len(run.results) == 8
    assert all(result.metrics.passed for result in run.results)
    assert test.metric[0].value == "1"


def test_result_filters_show_measured_failure(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DEVSEC_BENCH_HOME", str(tmp_path))
    database = Database(tmp_path / "history.db")
    database.save(run_suite(discover()[:1], AgentConfig()))
    database.save(run_suite(discover()[:1], AgentConfig(max_iterations=1)))
    test = AppTest.from_file(
        str(Path(__file__).parents[1] / "src/devsec_bench/dashboard/app.py")
    ).run(timeout=30)
    test.radio[0].set_value("Benchmark Runs").run(timeout=30)
    next(field for field in test.multiselect if field.label == "Status").set_value(
        ["Budget exhausted"]
    ).run(timeout=30)
    assert not test.exception
    assert len(test.dataframe[0].value) == 1
    assert test.dataframe[0].value.iloc[0]["Status"] == "Budget exhausted"


def test_settings_apply_to_dashboard_execution(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DEVSEC_BENCH_HOME", str(tmp_path))
    test = AppTest.from_file(
        str(Path(__file__).parents[1] / "src/devsec_bench/dashboard/app.py")
    ).run(timeout=30)
    test.radio[0].set_value("Settings").run(timeout=30)
    next(field for field in test.number_input if field.label == "Maximum iterations").set_value(1)
    next(button for button in test.button if button.label == "Save session defaults").click().run(
        timeout=30
    )
    next(button for button in test.button if button.label == "Start reference run").click().run(
        timeout=30
    )
    assert not test.exception
    assert all(
        result.output.status == "budget"
        for result in Database(tmp_path / "history.db").latest().results
    )


def test_corrupt_history_has_clear_error_state(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DEVSEC_BENCH_HOME", str(tmp_path))
    (tmp_path / "history.db").write_text("invalid database")
    test = AppTest.from_file(
        str(Path(__file__).parents[1] / "src/devsec_bench/dashboard/app.py")
    ).run(timeout=30)
    assert not test.exception
    assert any("could not be read" in error.value for error in test.error)


def test_run_action_preserves_corrupt_history_without_traceback(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DEVSEC_BENCH_HOME", str(tmp_path))
    path = tmp_path / "history.db"
    path.write_text("invalid database")
    test = AppTest.from_file(
        str(Path(__file__).parents[1] / "src/devsec_bench/dashboard/app.py")
    ).run(timeout=30)
    next(button for button in test.button if button.label == "Start reference run").click().run(
        timeout=30
    )
    assert not test.exception
    assert path.read_text() == "invalid database"
    assert any("could not be completed" in error.value for error in test.error)
