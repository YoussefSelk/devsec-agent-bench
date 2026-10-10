from typing import Any

from devsec_bench.models import Run


def summary(run: Run) -> dict[str, Any]:
    results = run.results
    count = len(results)
    costs = [r.estimated_cost for r in results]
    tokens = [r.output.usage.total_tokens for r in results]
    return {
        "id": run.id,
        "timestamp": run.timestamp,
        "agent": run.config.agent,
        "provider": run.config.provider if run.config.agent == "llm" else "offline",
        "model": run.config.model or "reference (source patterns)",
        "scenarios": count,
        "passed": sum(r.metrics.passed for r in results),
        "success_rate": sum(r.metrics.passed for r in results) / count if count else 0,
        "precision": sum(r.metrics.precision for r in results) / count if count else None,
        "recall": sum(r.metrics.recall for r in results) / count if count else None,
        "policy_violations": sum(r.metrics.policy_violations for r in results),
        "tool_calls": sum(len(r.events) for r in results),
        "average_latency": sum(r.duration for r in results) / count if count else None,
        "timeout_rate": sum(r.output.status == "timeout" for r in results) / count if count else 0,
        "error_rate": sum(r.output.status == "error" for r in results) / count if count else 0,
        "estimated_cost": sum(c for c in costs if c is not None)
        if costs and all(c is not None for c in costs)
        else None,
        "total_tokens": sum(t for t in tokens if t is not None)
        if tokens and all(t is not None for t in tokens)
        else None,
        "interrupted": run.interrupted,
    }


def compare(first: Run, second: Run) -> dict[str, Any]:
    left, right = summary(first), summary(second)
    return {
        "runs": [left, right],
        "success_rate_delta": right["success_rate"] - left["success_rate"],
        "comparable_suite": first.suite_digest == second.suite_digest,
        "note": "Differences require matching fixtures, repetition counts and configurations for causal interpretation.",
    }
