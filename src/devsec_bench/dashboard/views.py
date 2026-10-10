"""Pure presentation data derived from measured, persisted runs."""

import hashlib
from typing import Any

import pandas as pd

from devsec_bench.models import Run, Scenario, ScenarioResult


def current_fixtures_match(run: Run, definitions: list[Scenario]) -> bool:
    """Verify current reference evidence against the recorded fixture fingerprint."""
    if not run.suite_digest or not run.results:
        return False
    ids = {result.scenario for result in run.results}
    scenarios = [scenario for scenario in definitions if scenario.id in ids]
    if {scenario.id for scenario in scenarios} != ids:
        return False
    digest = hashlib.sha256()
    for scenario in scenarios:
        digest.update(scenario.model_dump_json(exclude={"repository"}).encode())
        for path in sorted(scenario.repository.rglob("*")):
            if path.is_file():
                digest.update(path.relative_to(scenario.repository).as_posix().encode())
                digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
    return digest.hexdigest() == run.suite_digest


def status_label(result: ScenarioResult) -> str:
    if result.metrics.policy_violations:
        return "Policy violation"
    statuses = {
        "error": "Execution error",
        "timeout": "Timed out",
        "budget": "Budget exhausted",
        "interrupted": "Interrupted",
    }
    return statuses.get(
        result.output.status, "Passed" if result.metrics.passed else "Evaluation failed"
    )


def overview_metrics(runs: list[Run]) -> dict[str, Any]:
    results = [result for run in runs for result in run.results]
    llm_results = [result for run in runs if run.config.agent == "llm" for result in run.results]
    prices_known = bool(llm_results) and all(
        result.estimated_cost is not None for result in llm_results
    )
    return {
        "runs": len(runs),
        "attempts": len(results),
        "success_rate": sum(result.metrics.passed for result in results) / len(results)
        if results
        else None,
        "policy_violations": sum(result.metrics.policy_violations for result in results),
        "average_latency": sum(result.duration for result in results) / len(results)
        if results
        else None,
        "estimated_cost": sum(result.estimated_cost or 0 for result in llm_results)
        if prices_known
        else None,
        "priced_attempts": sum(result.estimated_cost is not None for result in llm_results),
        "llm_attempts": len(llm_results),
    }


def history_rows(runs: list[Run]) -> list[dict[str, Any]]:
    rows = []
    for run in runs:
        model = run.config.model or "Reference baseline"
        for result in run.results:
            rows.append(
                {
                    "Run ID": run.id,
                    "Scenario": result.scenario,
                    "Name": result.name,
                    "Agent / Model": model,
                    "Agent": run.config.agent,
                    "Status": status_label(result),
                    "Success rate": float(result.metrics.passed),
                    "Duration (s)": result.duration,
                    "Tokens": result.output.usage.total_tokens,
                    "Estimated cost ($)": result.estimated_cost,
                    "Execution date": run.timestamp,
                    "Precision": result.metrics.precision,
                    "Recall": result.metrics.recall,
                    "Policy violations": result.metrics.policy_violations,
                    "Repetition": result.repetition,
                }
            )
    return rows


def scenario_rollup(runs: list[Run]) -> pd.DataFrame:
    data = pd.DataFrame(history_rows(runs))
    if data.empty:
        return pd.DataFrame(
            columns=["Scenario", "Name", "Attempts", "Success rate", "Precision", "Recall"]
        )
    return data.groupby(["Scenario", "Name"], as_index=False).agg(
        **{
            "Attempts": ("Run ID", "size"),
            "Success rate": ("Success rate", "mean"),
            "Precision": ("Precision", "mean"),
            "Recall": ("Recall", "mean"),
        }
    )


def model_rollup(runs: list[Run]) -> pd.DataFrame:
    data = pd.DataFrame(history_rows(runs))
    if data.empty:
        return pd.DataFrame(
            columns=[
                "Agent / Model",
                "Agent",
                "Attempts",
                "Passed",
                "Failed",
                "Success rate",
                "Mean latency (s)",
            ]
        )
    grouped = data.groupby(["Agent / Model", "Agent"], as_index=False).agg(
        **{
            "Attempts": ("Run ID", "size"),
            "Passed": ("Success rate", "sum"),
            "Success rate": ("Success rate", "mean"),
            "Mean latency (s)": ("Duration (s)", "mean"),
        }
    )
    grouped["Failed"] = grouped["Attempts"] - grouped["Passed"]
    return grouped


def run_rows(runs: list[Run]) -> list[dict[str, Any]]:
    data = []
    for run in runs:
        statuses = [status_label(result) for result in run.results]
        priority = [
            "Policy violation",
            "Execution error",
            "Timed out",
            "Budget exhausted",
            "Evaluation failed",
        ]
        outcome = (
            "Interrupted"
            if run.interrupted
            else next(
                (label for label in priority if label in statuses),
                "Passed" if statuses else "Pending",
            )
        )
        ids = sorted({result.scenario for result in run.results})
        data.append(
            {
                "Run ID": run.id,
                "Benchmark": ids[0]
                if len(ids) == 1
                else f"{len(ids)} benchmark results"
                if ids
                else "Awaiting results",
                "Agent / Model": run.config.model or "Offline demo",
                "Outcome": outcome,
                "Checks": f"{sum(result.metrics.passed for result in run.results)}/{len(run.results)} passed",
                "Date": run.timestamp,
                "Scenario time": sum(result.duration for result in run.results),
                "Policy violations": sum(
                    result.metrics.policy_violations for result in run.results
                ),
            }
        )
    return data


def aligned_results(first: Run, second: Run) -> list[dict[str, Any]]:
    left = {(result.scenario, result.repetition): result for result in first.results}
    right = {(result.scenario, result.repetition): result for result in second.results}
    data = []
    for scenario, repetition in sorted(left.keys() | right.keys()):
        a, b = left.get((scenario, repetition)), right.get((scenario, repetition))
        data.append(
            {
                "Scenario": scenario,
                "Repetition": repetition,
                "Run A outcome": status_label(a) if a else "No result",
                "Run B outcome": status_label(b) if b else "No result",
                "Run A recall": a.metrics.recall if a else None,
                "Run B recall": b.metrics.recall if b else None,
                "Recall delta": b.metrics.recall - a.metrics.recall if a and b else None,
                "Precision delta": b.metrics.precision - a.metrics.precision if a and b else None,
                "Duration delta (s)": b.duration - a.duration if a and b else None,
                "Run A violations": a.metrics.policy_violations if a else None,
                "Run B violations": b.metrics.policy_violations if b else None,
            }
        )
    return data
