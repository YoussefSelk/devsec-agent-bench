"""Task-based lists, benchmark index, evidence comparison and documentation."""

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from devsec_bench.benchmarks.loader import discover
from devsec_bench.dashboard.navigation import go, new_run
from devsec_bench.dashboard.theme import chart, status_badge, value
from devsec_bench.dashboard.views import aligned_results, run_rows
from devsec_bench.evaluation.comparison import compare as compare_runs
from devsec_bench.models import Run


def runs_index(runs: list[Run]) -> None:
    title, action = st.columns([5, 1.5])
    title.title("Evaluation runs")
    title.caption(
        "Inspect what an agent did, what it found, and whether it stayed within its permissions."
    )
    if action.button("New run", type="primary", width="stretch"):
        new_run()
    if not runs:
        st.divider()
        st.subheader("Your first evaluation")
        st.write(
            "Review small, authorized sample applications without changing or executing them. The offline demo needs no account or credentials and gives you a real finding and an inspectable action log."
        )
        st.info("No evaluation runs yet.")
        if st.button("Try the offline demo", type="primary"):
            new_run("SEC-001")
        if st.button("Explore benchmarks", type="tertiary"):
            go("Benchmarks")
        return
    data = run_rows(runs)
    search = st.text_input("Search runs", placeholder="Run ID, benchmark or model")
    filters = st.columns(3)
    outcome = filters[0].selectbox(
        "Outcome", ["All outcomes", *sorted({str(row["Outcome"]) for row in data})]
    )
    model = filters[1].selectbox(
        "Agent / model", ["All agents", *sorted({str(row["Agent / Model"]) for row in data})]
    )
    order = filters[2].selectbox("Sort by date", ["Newest first", "Oldest first"])
    filtered = [
        row
        for row in data
        if (outcome == "All outcomes" or row["Outcome"] == outcome)
        and (model == "All agents" or row["Agent / Model"] == model)
        and (
            not search
            or search.casefold() in " ".join(str(item) for item in row.values()).casefold()
        )
    ]
    filtered.sort(key=lambda row: str(row["Date"]), reverse=order == "Newest first")
    st.caption(
        f"{len(filtered)} of {len(data)} recorded runs · Scenario time sums measured analysis durations"
    )
    if not filtered:
        st.info(
            "No runs match your search and filters. Clear a filter or search another identifier."
        )
    for row in filtered:
        st.divider()
        heading, details = st.columns([4, 2])
        with heading:
            if st.button(
                f"{str(row['Run ID'])[:8]} / {row['Benchmark']}",
                key=f"open_{row['Run ID']}",
                type="tertiary",
            ):
                go("Runs", str(row["Run ID"]), "Outcome")
            st.write(f"{row['Agent / Model']} · {row['Checks']}")
        with details:
            status_badge(str(row["Outcome"]))
            st.caption(
                f"{str(row['Date'])[:19].replace('T', ' ')} UTC · {float(row['Scenario time']):.3f}s scenario time"
            )


def benchmarks() -> None:
    st.title("Benchmark catalog")
    st.caption(
        "Eight local, synthetic tasks. Read the objective and permissions before evaluating an agent."
    )
    search = st.text_input(
        "Search benchmarks", placeholder="Input validation, logging, dependencies…"
    )
    definitions = [
        scenario
        for scenario in discover()
        if not search
        or search.casefold() in f"{scenario.id} {scenario.name} {scenario.description}".casefold()
    ]
    if not definitions:
        st.info("No benchmarks match that search.")
    for scenario in definitions:
        st.divider()
        content, action = st.columns([5, 1.5])
        content.markdown(f"### {scenario.id} · {scenario.name}")
        content.caption(
            f"{scenario.difficulty.capitalize()} · {scenario.timeout:g}s limit · {scenario.max_iterations} iterations"
        )
        content.write(
            "Review a small application, identify the security mistake, cite its location and recommend a correction."
        )
        if action.button(
            "Evaluate", key=f"evaluate_{scenario.id}", type="secondary", width="stretch"
        ):
            new_run(scenario.id)
        with st.expander(f"Task and permitted capabilities · {scenario.id}"):
            st.write(scenario.instructions)
            st.write(
                "The agent may inspect only this repository's text. It cannot modify files, execute commands or read secrets."
            )
            st.code("\n".join(scenario.tools), language="text")
            st.caption(
                "Expected answer metadata is reserved for post-run evaluation inspection, not this agent-facing workflow."
            )


def comparison(runs: list[Run]) -> None:
    st.title("Compare two runs")
    st.caption("Align benchmark outcomes and evidence. Deltas are Run B minus Run A.")
    completed = [run for run in runs if run.results]
    if len(completed) < 2:
        st.info(
            "Record two evaluations to compare their results. The offline demo is enough to try this workflow."
        )
        if st.button("New run", type="primary"):
            new_run()
        return
    columns = st.columns(2)
    first = columns[0].selectbox(
        "Run A",
        completed,
        format_func=lambda run: f"{run.id[:8]} · {run.config.model or 'Offline demo'}",
        key="compare_a",
    )
    second = columns[1].selectbox(
        "Run B",
        completed,
        index=1,
        format_func=lambda run: f"{run.id[:8]} · {run.config.model or 'Offline demo'}",
        key="compare_b",
    )
    comparison = compare_runs(first, second)
    aligned = aligned_results(first, second)
    if first.id == second.id:
        st.info("Select a different Run B to compare two executions.")
        return
    if not first.suite_digest or not second.suite_digest:
        st.warning("Fixture compatibility is unknown because a recorded fingerprint is missing.")
    if not comparison["comparable_suite"] or {
        (item.scenario, item.repetition) for item in first.results
    } != {(item.scenario, item.repetition) for item in second.results}:
        st.warning(
            "These runs do not cover identical benchmark fixtures and repetitions. Missing results are shown explicitly; differences are not directly comparable."
        )
    st.write(f"**Success-rate delta:** {comparison['success_rate_delta']:+.1%}")
    st.download_button(
        "Export comparison CSV",
        pd.DataFrame(aligned).to_csv(index=False),
        f"compare-{first.id[:8]}-{second.id[:8]}.csv",
        "text/csv",
    )
    st.download_button(
        "Export comparison JSON",
        json.dumps({**comparison, "aligned_results": aligned}, indent=2),
        "comparison.json",
        "application/json",
    )
    st.divider()
    selected = st.selectbox(
        "Aligned benchmark",
        aligned,
        format_func=lambda row: f"{row['Scenario']} · repetition {row['Repetition']}",
    )
    sides = st.columns(2)
    for side, label, run in [(sides[0], "Run A", first), (sides[1], "Run B", second)]:
        with side:
            st.markdown(f"### {label} / {run.id[:8]}")
            st.caption(run.config.model or "Offline demo")
            result = next(
                (
                    item
                    for item in run.results
                    if (item.scenario, item.repetition)
                    == (selected["Scenario"], selected["Repetition"])
                ),
                None,
            )
            status_badge(str(selected[f"{label} outcome"]))
            if result:
                st.write(
                    f"**Precision:** {value(result.metrics.precision, 'percent')} · **Recall:** {value(result.metrics.recall, 'percent')}"
                )
                st.write(f"**Permission violations:** {result.metrics.policy_violations}")
                st.write(f"**Duration:** {value(result.duration, 'seconds')}")
                st.write(f"**Cost:** {value(result.estimated_cost, 'cost')}")
                st.caption(
                    result.output.error or f"{len(result.output.findings)} reported finding(s)"
                )
                if st.button("Inspect this run", key=f"inspect_compare_{label}"):
                    go("Runs", run.id, "Evidence", result.scenario, result.repetition)
            else:
                st.write("No benchmark result was recorded on this side.")
    st.divider()
    st.write(
        f"**Recall delta:** {value(selected['Recall delta'], 'percent')} · **Precision delta:** {value(selected['Precision delta'], 'percent')} · **Duration delta:** {value(selected['Duration delta (s)'], 'seconds')}"
    )
    with st.expander("All aligned metrics"):
        st.dataframe(pd.DataFrame(aligned), hide_index=True, width="stretch")
    with st.expander("Optional latency difference view"):
        data = pd.DataFrame(aligned).dropna(subset=["Duration delta (s)"])
        if not data.empty:
            chart(px.bar(data, x="Duration delta (s)", y="Scenario", orientation="h"))
    st.caption(
        "Compare matching fixtures and repetition counts. Different agent limits, provider behavior and runtime conditions can affect results. Reference-demo performance does not predict LLM performance."
    )


def documentation() -> None:
    st.title("Reading an evaluation")
    st.write(
        "DevSec Agent Bench evaluates how an agent reviews authorized sample applications. It records what the agent reported, what it did, and which benchmark checks passed."
    )
    st.subheader("Start with the offline demo")
    st.write(
        "Choose New run, select a benchmark, keep Offline demo, review permissions and start. No account or provider credentials are required."
    )
    st.subheader("Understand the outcome")
    st.write(
        "Passed means findings, permissions and reliable execution all passed. Evaluation failed means a finding or correction check did not match. Budget exhausted or Timed out means execution stopped early. Policy violation means the agent requested forbidden access."
    )
    st.subheader("Inspect the evidence")
    st.write(
        "Findings explains the affected file and suggested correction. Agent actions shows each tool request and permission decision. Evidence exposes the structural evaluator and its limits. Timing & usage separates measured duration from unavailable provider usage or prices."
    )
    st.subheader("Reproduce and export")
    st.write(
        "Open a run's Export & reproduce menu to download JSON, CSV or HTML and inspect the original configuration. Model outputs may vary; fixture inputs and the offline demo are deterministic."
    )
    st.code(
        "devsec-bench run --agent reference\ndevsec-bench dashboard --port 8517\ndevsec-mcp --scenario SEC-001",
        language="bash",
    )
    st.link_button(
        "Technical guide",
        "https://github.com/YoussefSelk/devsec-agent-bench/blob/main/docs/reference.md",
    )
    st.link_button(
        "Source & contribution guide", "https://github.com/YoussefSelk/devsec-agent-bench"
    )


def preferences(home: Path) -> None:
    with st.popover("Preferences"):
        st.caption("Session defaults for new evaluations")
        defaults = st.session_state.get(
            "offline_defaults", {"max_iterations": 20, "timeout": 30.0, "concurrency": 1, "seed": 0}
        )
        with st.form("preferences"):
            iterations = st.number_input(
                "Default iteration limit",
                min_value=1,
                max_value=100,
                value=int(defaults["max_iterations"]),
            )
            timeout = st.number_input(
                "Default time limit (seconds)",
                min_value=1.0,
                max_value=600.0,
                value=float(defaults["timeout"]),
            )
            concurrency = st.number_input(
                "Default workers", min_value=1, max_value=32, value=int(defaults["concurrency"])
            )
            if st.form_submit_button("Save preferences"):
                st.session_state["offline_defaults"] = {
                    "max_iterations": iterations,
                    "timeout": timeout,
                    "concurrency": concurrency,
                    "seed": defaults["seed"],
                }
                st.success("Saved for this browser session.")
        st.caption("History location")
        st.code(str(home), language="text", wrap_lines=True)
        st.caption(
            "Provider credentials are environment variables and never displayed or entered here."
        )
