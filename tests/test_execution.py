from pathlib import Path

import pytest

from devsec_bench.agents.reference import ReferenceAgent
from devsec_bench.benchmarks.loader import discover
from devsec_bench.benchmarks.runner import run_suite
from devsec_bench.evaluation.evaluator import evaluate
from devsec_bench.models import AgentConfig, AgentOutput, Finding, ToolEvent
from devsec_bench.tools.registry import Registry


def test_reference_reads_source_deterministically():
    for scenario in discover():
        outputs = []
        for _ in range(2):
            registry = Registry(scenario.repository, scenario.tools)
            outputs.append(ReferenceAgent().run(scenario.context(), registry, AgentConfig()))
            assert registry.events
            assert all(e.authorized for e in registry.events)
        assert outputs[0] == outputs[1]
        assert evaluate(scenario.expected, outputs[0], registry.events).passed


def test_reference_changes_when_source_changes(tmp_path: Path):
    (tmp_path / "app.py").write_text("def connect():\n    return 'safe'\n")
    scenario = discover()[0]
    output = ReferenceAgent().run(
        scenario.context(), Registry(tmp_path, scenario.tools), AgentConfig()
    )
    assert output.findings == []


def test_metrics_duplicates_locations_remediations_and_safety():
    scenario = discover()[0]
    finding = Finding(
        category="hardcoded_credentials",
        file="app.py",
        line=1,
        explanation="Embedded credential",
        remediation="Read from environment",
        action="use_environment",
    )
    output = AgentOutput(findings=[finding, finding])
    metrics = evaluate(scenario.expected, output, [])
    assert (metrics.true_positives, metrics.false_positives, metrics.false_negatives) == (1, 1, 0)
    assert metrics.precision == 0.5
    assert metrics.recall == 1
    assert not metrics.passed
    denied = ToolEvent(sequence=1, tool="unknown", arguments={}, authorized=False)
    assert not evaluate(scenario.expected, AgentOutput(findings=[finding]), [denied]).passed
    assert not evaluate(
        scenario.expected,
        AgentOutput(findings=[finding.model_copy(update={"action": "ignore"})]),
        [],
    ).correctness
    assert (
        evaluate(
            scenario.expected, AgentOutput(findings=[finding.model_copy(update={"line": 3})]), []
        ).false_negatives
        == 1
    )
    assert evaluate(scenario.expected, AgentOutput(), []).recall == 0


def test_iteration_limits_fail_without_fake_success():
    scenario = discover()[0]
    output = ReferenceAgent().run(
        scenario.context(),
        Registry(scenario.repository, scenario.tools),
        AgentConfig(max_iterations=1),
    )
    assert output.status == "budget"
    assert not evaluate(scenario.expected, output, []).passed


def test_concurrent_repetitions_are_isolated_and_fixture_unchanged():
    scenarios = discover()
    before = (scenarios[0].repository / "app.py").read_bytes()
    run = run_suite(scenarios, AgentConfig(), repetitions=2, concurrency=4)
    assert len(run.results) == 16
    assert all(r.metrics.passed for r in run.results)
    assert (scenarios[0].repository / "app.py").read_bytes() == before
    assert len({(r.scenario, r.repetition) for r in run.results}) == 16


def test_partial_failure_keeps_other_results():
    scenarios = discover()[:2]
    scenarios[0] = scenarios[0].model_copy(update={"tools": ["list_files"]})
    run = run_suite(scenarios, AgentConfig(), concurrency=2)
    assert len(run.results) == 2
    assert not run.results[0].metrics.passed
    assert run.results[1].metrics.passed


def test_interruption_preserves_finishing_workers(monkeypatch):
    def interrupted(_):
        raise KeyboardInterrupt

    monkeypatch.setattr("devsec_bench.benchmarks.runner.as_completed", interrupted)
    snapshots = []
    run = run_suite(
        discover()[:1],
        AgentConfig(),
        on_update=lambda value: snapshots.append(value.model_copy(deep=True)),
    )
    assert run.interrupted
    assert len(run.results) == 1
    assert run.results[0].metrics.passed
    assert len(snapshots[-1].results) == 1


@pytest.mark.parametrize("kwargs", [{"repetitions": 0}, {"concurrency": 0}])
def test_invalid_runner_limits(kwargs):
    with pytest.raises(ValueError):
        run_suite(discover(), AgentConfig(), **kwargs)
