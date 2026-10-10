from pathlib import Path

from streamlit.testing.v1 import AppTest

from devsec_bench.agents.reference import ReferenceAgent
from devsec_bench.benchmarks.loader import discover
from devsec_bench.benchmarks.runner import run_suite
from devsec_bench.models import AgentConfig, Run
from devsec_bench.storage.database import Database

APP = Path(__file__).parents[1] / "src/devsec_bench/dashboard/app.py"


def press(test, label):
    next(button for button in test.button if button.label == label).click().run(timeout=30)
    assert not test.exception


def start(test):
    press(test, "New run")
    press(test, "Continue")
    press(test, "Review permissions")
    press(test, "Start evaluation")


def test_dashboard_reads_real_runs_and_purposeful_navigation(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DEVSEC_BENCH_HOME", str(tmp_path))
    run = run_suite(discover(), AgentConfig())
    Database(tmp_path / "history.db").save(run)
    test = AppTest.from_file(str(APP)).run(timeout=30)
    assert not test.exception
    assert any(button.key == f"open_{run.id}" for button in test.button)
    assert not test.metric
    for page in ["Benchmarks", "Compare", "Documentation", "Runs"]:
        test.radio[0].set_value(page).run(timeout=30)
        assert not test.exception


def test_first_run_flow_launches_real_demo(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DEVSEC_BENCH_HOME", str(tmp_path))
    test = AppTest.from_file(str(APP)).run(timeout=30)
    assert test.info
    start(test)
    run = Database(tmp_path / "history.db").latest()
    assert len(run.results) == 8
    assert all(result.metrics.passed for result in run.results)
    assert test.query_params["run"] == run.id
    assert any("expected" in text.value.lower() for text in test.markdown)


def test_failed_run_explains_iteration_limit_and_raw_details(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DEVSEC_BENCH_HOME", str(tmp_path))
    run = run_suite(discover()[:1], AgentConfig(max_iterations=1))
    Database(tmp_path / "history.db").save(run)
    test = AppTest.from_file(str(APP)).run(timeout=30)
    next(button for button in test.button if button.key == f"open_{run.id}").click().run(timeout=30)
    assert not test.exception
    assert any("iteration limit" in text.value.lower() for text in test.markdown)
    next(field for field in test.radio if field.label == "Inspect").set_value("Agent actions").run(
        timeout=30
    )
    assert not test.exception
    assert any("list_files" in expander.label for expander in test.expander)


def test_denied_tool_is_visible_in_inspection(tmp_path: Path, monkeypatch):
    class DeniedAgent:
        def run(self, context, registry, config):
            registry.call("read_file", {"path": "../private"})
            return ReferenceAgent().run(context, registry, config)

    monkeypatch.setenv("DEVSEC_BENCH_HOME", str(tmp_path))
    run = run_suite(discover()[:1], AgentConfig(), factory=DeniedAgent)
    Database(tmp_path / "history.db").save(run)
    test = AppTest.from_file(str(APP)).run(timeout=30)
    next(button for button in test.button if button.key == f"open_{run.id}").click().run(timeout=30)
    next(field for field in test.radio if field.label == "Inspect").set_value("Agent actions").run(
        timeout=30
    )
    assert not test.exception
    assert any("Denied" in expander.label for expander in test.expander)


def test_search_filters_actual_runs(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DEVSEC_BENCH_HOME", str(tmp_path))
    database = Database(tmp_path / "history.db")
    good = run_suite(discover()[:1], AgentConfig())
    failed = run_suite(discover()[:1], AgentConfig(max_iterations=1))
    database.save(good)
    database.save(failed)
    test = AppTest.from_file(str(APP)).run(timeout=30)
    next(field for field in test.selectbox if field.label == "Outcome").set_value(
        "Budget exhausted"
    ).run(timeout=30)
    assert [button.key for button in test.button if str(button.key).startswith("open_")] == [
        f"open_{failed.id}"
    ]
    next(field for field in test.text_input if field.label == "Search runs").set_value(good.id).run(
        timeout=30
    )
    assert not any(str(button.key).startswith("open_") for button in test.button)
    assert test.info


def test_comparison_and_pending_snapshots(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DEVSEC_BENCH_HOME", str(tmp_path))
    database = Database(tmp_path / "history.db")
    database.save(run_suite(discover()[:1], AgentConfig()))
    database.save(run_suite(discover()[:1], AgentConfig(max_iterations=1)))
    database.save(Run(id="pending", config=AgentConfig()))
    test = AppTest.from_file(str(APP)).run(timeout=30)
    test.radio[0].set_value("Compare").run(timeout=30)
    assert not test.exception
    assert not test.warning
    test.radio[0].set_value("Runs").run(timeout=30)
    next(button for button in test.button if button.key == "open_pending").click().run(timeout=30)
    assert not test.exception
    assert test.info


def test_corrupt_history_launch_is_safe(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DEVSEC_BENCH_HOME", str(tmp_path))
    path = tmp_path / "history.db"
    path.write_text("invalid database")
    test = AppTest.from_file(str(APP)).run(timeout=30)
    assert not any("No evaluation runs yet" in item.value for item in test.info)
    start(test)
    assert path.read_text() == "invalid database"
    assert test.error


def test_missing_llm_credentials_leave_offline_flow_available(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DEVSEC_BENCH_HOME", str(tmp_path))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    test = AppTest.from_file(str(APP)).run(timeout=30)
    press(test, "New run")
    press(test, "Continue")
    next(field for field in test.radio if field.label == "Choose an agent").set_value(
        "LLM agent"
    ).run(timeout=30)
    assert any("credential" in text.value.lower() for text in test.info)
    next(field for field in test.radio if field.label == "Choose an agent").set_value(
        "Offline demo"
    ).run(timeout=30)
    press(test, "Review permissions")
    press(test, "Start evaluation")
    assert Database(tmp_path / "history.db").latest().config.agent == "reference"


def test_navigation_tracks_external_bookmark_changes(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DEVSEC_BENCH_HOME", str(tmp_path))
    test = AppTest.from_file(str(APP)).run(timeout=30)
    test.query_params["view"] = "Documentation"
    test.run(timeout=30)
    assert test.radio[0].value == "Documentation"
    test.radio[0].set_value("Runs").run(timeout=30)
    assert test.query_params["view"] == "Runs"
    assert any(heading.value == "Evaluation runs" for heading in test.title)


def test_inspection_bookmark_preserves_benchmark_and_section(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DEVSEC_BENCH_HOME", str(tmp_path))
    run = run_suite(discover(), AgentConfig())
    Database(tmp_path / "history.db").save(run)
    test = AppTest.from_file(str(APP))
    test.query_params.update(
        {"view": "Runs", "run": run.id, "scenario": "SEC-008", "section": "Findings"}
    )
    test.run(timeout=30)
    assert not test.exception
    assert (
        next(field for field in test.selectbox if field.label == "Benchmark result").value.scenario
        == "SEC-008"
    )
    assert next(field for field in test.radio if field.label == "Inspect").value == "Findings"
    test.query_params["section"] = "Agent actions"
    test.run(timeout=30)
    assert next(field for field in test.radio if field.label == "Inspect").value == "Agent actions"
