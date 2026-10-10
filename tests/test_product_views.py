from devsec_bench.benchmarks.loader import discover
from devsec_bench.benchmarks.runner import run_suite
from devsec_bench.dashboard.views import aligned_results, current_fixtures_match, run_rows
from devsec_bench.models import AgentConfig, Run


def test_run_index_is_one_row_per_run_and_separates_failures():
    good = run_suite(discover()[:2], AgentConfig())
    failed = run_suite(discover()[:1], AgentConfig(max_iterations=1))
    rows = run_rows([good, failed])
    assert len(rows) == 2
    assert rows[0]["Outcome"] == "Passed"
    assert rows[0]["Checks"] == "2/2 passed"
    assert rows[1]["Outcome"] == "Budget exhausted"
    pending = run_rows([Run(id="pending", config=AgentConfig())])
    assert pending[0]["Outcome"] == "Pending"


def test_comparison_aligns_missing_results_without_inventing_deltas():
    first = run_suite(discover()[:2], AgentConfig())
    second = run_suite(discover()[:1], AgentConfig(max_iterations=1))
    rows = aligned_results(first, second)
    assert len(rows) == 2
    assert rows[0]["Recall delta"] == -1
    assert rows[1]["Run B outcome"] == "No result"
    assert rows[1]["Recall delta"] is None


def test_historical_reference_answers_require_matching_fingerprint():
    definitions = discover()
    run = run_suite(definitions[:1], AgentConfig())
    assert current_fixtures_match(run, definitions)
    run.suite_digest = "changed-fixtures"
    assert not current_fixtures_match(run, definitions)
    run.suite_digest = ""
    assert not current_fixtures_match(run, definitions)
