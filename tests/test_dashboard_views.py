from devsec_bench.benchmarks.loader import discover
from devsec_bench.benchmarks.runner import run_suite
from devsec_bench.dashboard.views import (
    history_rows,
    model_rollup,
    overview_metrics,
    scenario_rollup,
    status_label,
)
from devsec_bench.models import AgentConfig


def test_overview_uses_weighted_scenario_measurements():
    good = run_suite(discover()[:2], AgentConfig())
    failed = run_suite(discover()[:1], AgentConfig(max_iterations=1))
    for result in good.results:
        result.duration = 2.0
    failed.results[0].duration = 8.0
    metrics = overview_metrics([good, failed])
    assert metrics["runs"] == 2
    assert metrics["success_rate"] == 2 / 3
    assert metrics["average_latency"] == 4.0
    assert metrics["estimated_cost"] is None
    assert metrics["policy_violations"] == 0


def test_rollups_and_rows_distinguish_failure_categories():
    good = run_suite(discover()[:1], AgentConfig())
    failed = run_suite(discover()[:1], AgentConfig(max_iterations=1))
    data = history_rows([good, failed])
    assert {row["Status"] for row in data} == {"Passed", "Budget exhausted"}
    assert all(row["Tokens"] is None for row in data)
    scenarios = scenario_rollup([good, failed])
    assert scenarios.iloc[0]["Attempts"] == 2
    assert scenarios.iloc[0]["Success rate"] == 0.5
    models = model_rollup([good, failed])
    assert models.iloc[0]["Passed"] == 1
    assert models.iloc[0]["Failed"] == 1
    result = good.results[0]
    result.metrics.policy_violations = 1
    assert status_label(result) == "Policy violation"
    result.metrics.policy_violations = 0
    result.output.status = "error"
    assert status_label(result) == "Execution error"


def test_empty_measures_are_unavailable():
    metrics = overview_metrics([])
    assert metrics["runs"] == 0
    assert metrics["success_rate"] is None
    assert metrics["estimated_cost"] is None
