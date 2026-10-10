"""Pure presentation data derived from measured, persisted runs."""

from typing import Any

import pandas as pd

from devsec_bench.models import Run, ScenarioResult


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
