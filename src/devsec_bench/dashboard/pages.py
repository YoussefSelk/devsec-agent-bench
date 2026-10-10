"""Native Streamlit analytics pages over existing benchmark domain objects."""

import pandas as pd
import plotly.express as px
import streamlit as st

from devsec_bench.benchmarks.loader import discover
from devsec_bench.dashboard.theme import COLORS, chart, status_badge, value
from devsec_bench.dashboard.views import (
    history_rows,
    model_rollup,
    overview_metrics,
    scenario_rollup,
    status_label,
)
from devsec_bench.evaluation.comparison import summary
from devsec_bench.models import Run
from devsec_bench.reporting.exporters import html_report, rows


def overview(runs: list[Run]) -> None:
    metrics = overview_metrics(runs)
    columns = st.columns(5)
    columns[0].metric("Benchmark runs", metrics["runs"])
    columns[1].metric("Success rate", value(metrics["success_rate"], "percent"))
    columns[2].metric("Policy violations", metrics["policy_violations"])
    columns[3].metric("Average latency", value(metrics["average_latency"], "seconds"))
    columns[4].metric("Estimated LLM cost", value(metrics["estimated_cost"], "cost"))
    st.caption(
        f"{metrics['attempts']} measured scenario attempts · Cost requires reported usage and configured prices · All history"
    )
    completed = [run for run in runs if run.results]
    if not completed:
        st.info("No evaluation results yet. Run an offline benchmark to establish your baseline.")
        return
    left, right = st.columns([1.2, 1])
    with left, st.container(border=True):
        st.markdown("**Success-rate trend**")
        statistics = pd.DataFrame([summary(run) for run in reversed(completed)])
        statistics["Executed"] = pd.to_datetime(statistics["timestamp"], utc=True)
        statistics["Success"] = statistics["success_rate"]
        figure = px.line(
            statistics,
            x="Executed",
            y="Success",
            markers=True,
            hover_data=["agent", "model", "scenarios"],
            color_discrete_sequence=[COLORS["blue"]],
        )
        figure.update_yaxes(range=[-0.03, 1.05], tickformat=".0%", title=None)
        figure.update_xaxes(title=None)
        chart(figure)
    with right, st.container(border=True):
        st.markdown("**Scenario performance**")
        scenarios = scenario_rollup(runs)
        figure = px.bar(
            scenarios,
            x="Success rate",
            y="Scenario",
            orientation="h",
            hover_data=["Name", "Attempts", "Precision", "Recall"],
            color_discrete_sequence=[COLORS["green"]],
        )
        figure.update_xaxes(range=[0, 1.05], tickformat=".0%", title=None)
        figure.update_yaxes(title=None, autorange="reversed")
        chart(figure)
    with st.container(border=True):
        st.markdown("**Evaluation outcomes by model**")
        models = model_rollup(runs)
        distribution = models.melt(
            id_vars=["Agent / Model"],
            value_vars=["Passed", "Failed"],
            var_name="Outcome",
            value_name="Scenario attempts",
        )
        figure = px.bar(
            distribution,
            x="Scenario attempts",
            y="Agent / Model",
            color="Outcome",
            orientation="h",
            color_discrete_map={"Passed": COLORS["green"], "Failed": COLORS["red"]},
        )
        figure.update_yaxes(title=None)
        chart(figure, 210)
    st.markdown("**Recent benchmark runs**")
    recent = [
        {
            "Run": run.id[:8],
            "Agent / Model": run.config.model or "Reference baseline",
            "Passed": f"{sum(r.metrics.passed for r in run.results)}/{len(run.results)}",
            "Success rate": summary(run)["success_rate"] if run.results else None,
            "Executed (UTC)": run.timestamp[:19].replace("T", " "),
            "State": "Interrupted" if run.interrupted else "Recorded" if run.results else "Pending",
        }
        for run in runs[:10]
    ]
    st.dataframe(
        pd.DataFrame(recent),
        hide_index=True,
        width="stretch",
        column_config={
            "Success rate": st.column_config.ProgressColumn(
                format="percent", min_value=0, max_value=1
            )
        },
    )


def benchmark_runs(runs: list[Run]) -> None:
    data = pd.DataFrame(history_rows(runs))
    if data.empty:
        st.info("No completed scenario results. Initial run snapshots remain available in Reports.")
        return
    filters = st.columns(3)
    agents = filters[0].multiselect("Agent / Model", sorted(data["Agent / Model"].unique()))
    statuses = filters[1].multiselect("Status", sorted(data["Status"].unique()))
    scenarios = filters[2].multiselect("Scenario", sorted(data["Scenario"].unique()))
    filtered = data
    for column, choices in [
        ("Agent / Model", agents),
        ("Status", statuses),
        ("Scenario", scenarios),
    ]:
        if choices:
            filtered = filtered[filtered[column].isin(choices)]
    st.caption(
        f"{len(filtered)} of {len(data)} measured scenario attempts · Click a column header to sort"
    )
    if filtered.empty:
        st.info("No results match these filters.")
        return
    display = filtered.copy()
    display["Run ID"] = display["Run ID"].str.slice(0, 8)
    display["Execution date"] = display["Execution date"].str.slice(0, 19).str.replace("T", " ")
    st.dataframe(
        display,
        hide_index=True,
        width="stretch",
        column_order=[
            "Run ID",
            "Scenario",
            "Agent / Model",
            "Status",
            "Success rate",
            "Duration (s)",
            "Tokens",
            "Estimated cost ($)",
            "Execution date",
            "Precision",
            "Recall",
        ],
        column_config={
            "Success rate": st.column_config.ProgressColumn(
                format="percent", min_value=0, max_value=1
            ),
            "Duration (s)": st.column_config.NumberColumn(format="%.3f"),
            "Estimated cost ($)": st.column_config.NumberColumn(format="$%.5f"),
            "Tokens": st.column_config.NumberColumn(format="%d"),
            "Execution date": st.column_config.TextColumn("Executed (UTC)"),
        },
    )
    st.caption(
        "Passed, evaluation failed, execution error, timeout, budget exhaustion and policy violation are distinct outcomes. A blank cost or token field means unavailable."
    )
    st.markdown("**Inspect a result**")
    keys = [
        (str(row["Run ID"]), str(row["Scenario"]), int(row["Repetition"]))
        for row in filtered.to_dict("records")
    ]
    chosen = st.selectbox(
        "Result", keys, format_func=lambda key: f"{key[0][:8]} / {key[1]} / repetition {key[2]}"
    )
    run = next(run for run in runs if run.id == chosen[0])
    result = next(
        result
        for result in run.results
        if (result.scenario, result.repetition) == (chosen[1], chosen[2])
    )
    with st.container(border=True):
        st.markdown(f"**{result.scenario} · {result.name}**")
        status_badge(status_label(result))
        quality, findings = st.tabs(["Evaluation", "Findings"])
        with quality:
            st.json(result.metrics.model_dump(), expanded=False)
            if result.output.error:
                st.error(result.output.error)
        with findings:
            if not result.output.findings:
                st.info("No findings returned in this result.")
            for finding in result.output.findings:
                st.markdown(f"**{finding.file}:{finding.line}** · `{finding.category}`")
                st.write(finding.explanation)
                st.caption(f"Correction: {finding.remediation}")


def scenarios(runs: list[Run]) -> None:
    definitions = discover()
    data = scenario_rollup(runs)
    st.caption(
        f"{len(definitions)} authorized synthetic repositories · Source analysis only · Pinned ground truth"
    )
    selected = st.selectbox(
        "Scenario", definitions, format_func=lambda scenario: f"{scenario.id} · {scenario.name}"
    )
    with st.container(border=True):
        header, difficulty = st.columns([4, 1])
        header.markdown(f"### {selected.id} · {selected.name}")
        difficulty.markdown(f"`{selected.difficulty.upper()}`")
        st.write(selected.description)
        cols = st.columns(3)
        cols[0].metric("Time limit", f"{selected.timeout:g}s")
        cols[1].metric("Iteration limit", selected.max_iterations)
        cols[2].metric("Authorized tools", len(selected.tools))
        task, evidence, reference = st.tabs(
            ["Task & permissions", "Measured performance", "Evaluator metadata"]
        )
        with task:
            st.markdown("**Agent task**")
            st.write(selected.instructions)
            st.markdown("**Tool allowlist**")
            st.code(" · ".join(selected.tools), language="text", wrap_lines=True)
            st.caption(
                "Repository alias: target · Read-only · No terminal or network tools · Secret paths denied"
            )
        with evidence:
            measured = data[data["Scenario"] == selected.id]
            if measured.empty:
                st.info("This scenario has no measured evaluations yet.")
            else:
                row = measured.iloc[0]
                cols = st.columns(3)
                cols[0].metric("Attempts", int(row["Attempts"]))
                cols[1].metric("Success rate", value(row["Success rate"], "percent"))
                cols[2].metric("Finding recall", value(row["Recall"], "percent"))
        with reference:
            st.caption(
                "Ground truth belongs to the evaluator. It is never included in an agent's task context."
            )
            with st.expander("Inspect evaluator-only reference findings"):
                st.json([finding.model_dump() for finding in selected.expected])


def comparison(runs: list[Run]) -> None:
    completed = [run for run in runs if run.results]
    if not completed:
        st.info("Complete an evaluation before comparing configurations.")
        return
    ids = st.multiselect(
        "Runs to compare",
        [run.id for run in completed],
        default=[run.id for run in completed[:2]],
        format_func=lambda key: next(
            f"{run.id[:8]} · {run.config.model or 'Reference'} · {run.timestamp[:19]}"
            for run in completed
            if run.id == key
        ),
    )
    selected = [run for run in completed if run.id in ids]
    if not selected:
        st.info("Select one or more measured runs.")
        return
    if len({run.suite_digest for run in selected}) > 1:
        st.warning(
            "These runs use different scenario sets or fixture digests. Compare results with that difference in mind."
        )
    statistics = pd.DataFrame([summary(run) for run in selected])
    statistics["Run"] = statistics["id"].str.slice(0, 8)
    left, right = st.columns(2)
    with left, st.container(border=True):
        st.markdown("**Success by configuration**")
        figure = px.bar(
            statistics,
            x="Run",
            y="success_rate",
            color="agent",
            hover_data=["model", "scenarios"],
            color_discrete_sequence=[COLORS["blue"], COLORS["green"]],
            labels={"success_rate": "Success rate"},
        )
        figure.update_yaxes(range=[0, 1.05], tickformat=".0%")
        chart(figure)
    with right, st.container(border=True):
        st.markdown("**Measured latency**")
        figure = px.bar(
            statistics,
            x="Run",
            y="average_latency",
            color="agent",
            hover_data=["model"],
            color_discrete_sequence=[COLORS["blue"], COLORS["green"]],
            labels={"average_latency": "Mean latency (s)"},
        )
        chart(figure)
    cost, usage = st.tabs(["Cost versus performance", "Token usage over time"])
    with cost:
        priced = statistics.dropna(subset=["estimated_cost"])
        if priced.empty:
            st.info(
                "No cost measurements available. LLM runs need provider usage and configured pricing."
            )
        else:
            figure = px.scatter(
                priced,
                x="average_latency",
                y="estimated_cost",
                color="model",
                hover_data=["Run", "success_rate"],
                labels={
                    "average_latency": "Mean latency (s)",
                    "estimated_cost": "Estimated cost ($)",
                },
            )
            chart(figure)
    with usage:
        known = statistics.dropna(subset=["total_tokens"])
        if known.empty:
            st.info(
                "These runs have no provider-reported token usage. Reference runs do not consume model tokens."
            )
        else:
            known = known.sort_values("timestamp")
            figure = px.line(
                known,
                x="timestamp",
                y="total_tokens",
                color="model",
                markers=True,
                labels={"timestamp": "Executed (UTC)", "total_tokens": "Reported tokens"},
            )
            chart(figure, 220)
    st.dataframe(
        statistics[
            [
                "Run",
                "agent",
                "model",
                "scenarios",
                "passed",
                "precision",
                "recall",
                "average_latency",
                "total_tokens",
                "estimated_cost",
            ]
        ],
        hide_index=True,
        width="stretch",
    )
    st.caption(
        "The reference baseline recognizes fixture-specific patterns. It is not a model performance measurement. Repetitions and configuration differences affect comparisons."
    )


def traces(run: Run) -> None:
    if not run.results:
        st.info("No execution events are available for this initial run snapshot.")
        return
    result = st.selectbox(
        "Scenario / repetition",
        run.results,
        format_func=lambda item: f"{item.scenario} · {item.name} · repetition {item.repetition}",
    )
    summary_cols = st.columns(3)
    summary_cols[0].metric("Tool calls", len(result.events))
    summary_cols[1].metric("Policy violations", result.metrics.policy_violations)
    summary_cols[2].metric("Execution duration", value(result.duration, "seconds"))
    status_badge(status_label(result))
    timeline, findings, evaluation = st.tabs(["Tool timeline", "Agent findings", "Evaluation"])
    with timeline:
        st.caption(
            "Observed tool requests and authorization decisions, in sequence. Raw agent reasoning and tool response bodies are not retained; response metadata is shown."
        )
        if not result.events:
            st.info("No tools were called before this execution ended.")
        for event in result.events:
            decision = "Allowed" if event.authorized else "Denied"
            with st.expander(
                f"{event.sequence:02} · {event.tool} · {decision} · {event.duration * 1000:.1f} ms",
                expanded=event.sequence == 1,
            ):
                st.caption(f"{event.timestamp} · UTC")
                status_badge("Passed" if event.authorized else "Policy violation")
                st.markdown("**Observed agent action**")
                st.write(f"Requested `{event.tool}` through the repository tool boundary.")
                request, response = st.columns(2)
                with request:
                    st.markdown("**Request metadata**")
                    st.json({"tool": event.tool, "arguments": event.arguments}, expanded=True)
                with response:
                    st.markdown("**Response metadata**")
                    st.json(
                        {
                            "bytes_returned": event.bytes_returned,
                            "error": event.error,
                            "duration_seconds": event.duration,
                        },
                        expanded=True,
                    )
                if event.error:
                    st.error(event.error)
    with findings:
        if result.output.error:
            st.error(result.output.error)
        st.json(result.output.model_dump(mode="json"), expanded=True)
    with evaluation:
        columns = st.columns(3)
        for column, label, passed in [
            (columns[0], "Correctness", result.metrics.correctness),
            (columns[1], "Tool safety", result.metrics.safe),
            (columns[2], "Execution reliability", result.metrics.reliable),
        ]:
            with column:
                st.markdown(f"**{label}**")
                status_badge("Passed" if passed else "Evaluation failed")
        st.json(result.metrics.model_dump(), expanded=True)
        st.caption(
            "Remediation validity checks structured actions and minimum text length; it is not a semantic proof of patch safety."
        )


def reports(run: Run) -> None:
    statistics = summary(run)
    cols = st.columns(3)
    cols[0].metric("Scenario attempts", len(run.results))
    cols[1].metric(
        "Success rate", value(statistics["success_rate"] if run.results else None, "percent")
    )
    cols[2].metric("Tool-policy violations", statistics["policy_violations"])
    exports, preview, config = st.tabs(
        ["Export reports", "Report summary", "Configuration snapshot"]
    )
    with exports, st.container(border=True):
        st.markdown("**Evidence ready to share**")
        st.caption(
            "Exports use sanitized persisted data. Unavailable metrics remain null or blank."
        )
        buttons = st.columns(3)
        buttons[0].download_button(
            "JSON report",
            run.model_dump_json(indent=2),
            f"{run.id}.json",
            "application/json",
            width="stretch",
        )
        buttons[1].download_button(
            "CSV results",
            pd.DataFrame(rows(run)).to_csv(index=False),
            f"{run.id}.csv",
            "text/csv",
            width="stretch",
        )
        buttons[2].download_button(
            "HTML report", html_report(run), f"{run.id}.html", "text/html", width="stretch"
        )
        st.caption("JUnit XML is also generated by the CLI for CI artifact collection.")
    with preview:
        st.json(statistics, expanded=True)
    with config:
        st.code(run.id, language="text")
        st.json(run.config.model_dump(mode="json"), expanded=True)
        st.caption(f"Fixture digest: {run.suite_digest or 'unavailable'}")


def settings(home: str) -> None:
    execution, storage = st.tabs(["Execution defaults", "History & security"])
    with execution, st.container(border=True):
        st.markdown("**Offline reference defaults**")
        st.caption(
            "Applies to runs launched in this dashboard session. Paid models are configured through the CLI."
        )
        defaults = st.session_state.get(
            "offline_defaults", {"max_iterations": 20, "timeout": 30.0, "concurrency": 2, "seed": 0}
        )
        with st.form("execution-defaults"):
            cols = st.columns(2)
            iterations = cols[0].number_input(
                "Maximum iterations",
                min_value=1,
                max_value=100,
                value=int(defaults["max_iterations"]),
            )
            timeout = cols[1].number_input(
                "Scenario timeout (seconds)",
                min_value=1.0,
                max_value=600.0,
                value=float(defaults["timeout"]),
            )
            concurrency = cols[0].number_input(
                "Concurrent workers", min_value=1, max_value=32, value=int(defaults["concurrency"])
            )
            seed = cols[1].number_input(
                "Random seed", min_value=0, max_value=2**31 - 1, value=int(defaults["seed"])
            )
            if st.form_submit_button("Save session defaults", type="primary"):
                st.session_state["offline_defaults"] = {
                    "max_iterations": iterations,
                    "timeout": timeout,
                    "concurrency": concurrency,
                    "seed": seed,
                }
                st.success("Execution defaults saved for this session.")
    with storage:
        st.markdown("**Local evaluation history**")
        st.code(home, language="text")
        st.markdown("**Execution boundary**")
        st.write(
            "Dashboard launches analyze trusted synthetic sources in separate temporary copies. Tools are read-only and allowlisted; no fixture code is executed. Use the CLI Docker option when container isolation is required."
        )
        st.code(
            "devsec-bench run --agent reference --isolation docker\ndevsec-bench run --agent llm --model MODEL_NAME --scenario SEC-001",
            language="bash",
            wrap_lines=True,
        )
        st.caption(
            "LLM credentials are environment variables. They are never displayed or entered through this dashboard."
        )
