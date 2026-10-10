"""Streamlit views over persisted benchmark data; no seeded or invented results."""

import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from devsec_bench.evaluation.comparison import summary
from devsec_bench.reporting.exporters import html_report, rows
from devsec_bench.storage.database import Database

st.set_page_config(page_title="DevSec Agent Bench", page_icon="🛡", layout="wide")
st.markdown(
    "<style>.block-container{padding-top:2rem}div[data-testid=stMetric]{background:#f0f4f8;color:#183047;padding:16px;border-radius:8px}h1{letter-spacing:-.04em}@media(max-width:900px){div[data-testid=stHorizontalBlock]:has(div[data-testid=stMetric]){flex-wrap:wrap}div[data-testid=stColumn]:has(div[data-testid=stMetric]){min-width:180px;flex:1 1 180px}}</style>",
    unsafe_allow_html=True,
)
st.title("DevSec Agent Bench")
st.caption("Controlled security-agent evaluation · Reproducible evidence · Read-only tools")
home = Path(os.environ.get("DEVSEC_BENCH_HOME", ".bench"))
database = Database(home / "history.db")
runs = database.list_runs()
st.sidebar.title("Explore benchmark history")
page = st.sidebar.radio(
    "View", ["Overview", "Benchmark Results", "Agent Comparison", "Execution Traces", "Reports"]
)
if not runs:
    st.info("No measured results yet. Run: devsec-bench run --agent reference")
    st.stop()

statistics = pd.DataFrame([summary(run) for run in runs])
statistics["run_label"] = statistics["id"].str.slice(0, 8)
selected_id = st.sidebar.selectbox(
    "Run",
    [run.id for run in runs],
    format_func=lambda value: next(
        f"{run.timestamp[:19]} · {run.config.agent} · {value[:8]}"
        for run in runs
        if run.id == value
    ),
)
selected = next(run for run in runs if run.id == selected_id)
data = pd.DataFrame(rows(selected))
if not selected.results and page != "Overview":
    st.info(
        "This run has no completed scenarios yet. Choose a completed run or refresh after execution."
    )
    st.stop()
st.sidebar.caption(
    f"Agent: {selected.config.agent}\n\nModel: {selected.config.model or 'Offline source-pattern reference'}"
)
st.sidebar.caption(
    "Token usage and cost stay unavailable when unreported. Reference runs are not LLM performance measurements."
)

if page == "Overview":
    st.subheader("Measured runs")
    total = sum(len(run.results) for run in runs)
    passed = sum(result.metrics.passed for run in runs for result in run.results)
    metrics = st.columns(5)
    metrics[0].metric("Total runs", len(runs))
    metrics[1].metric("Success rate", f"{passed / total:.0%}" if total else "unavailable")
    durations = [result.duration for run in runs for result in run.results]
    metrics[2].metric(
        "Average latency", f"{sum(durations) / len(durations):.3f}s" if durations else "unavailable"
    )
    costs = statistics["estimated_cost"].dropna()
    metrics[3].metric(
        "Mean known run cost", f"${costs.mean():.4f}" if not costs.empty else "unavailable"
    )
    metrics[4].metric("Policy violations", int(statistics["policy_violations"].sum()))
    st.plotly_chart(
        px.bar(
            statistics,
            x="run_label",
            y="success_rate",
            color="agent",
            title="Success rate by measured run",
            range_y=[0, 1],
            labels={"id": "Run ID", "success_rate": "Success rate"},
        ),
        width="stretch",
    )
    st.dataframe(
        statistics[
            [
                "id",
                "agent",
                "model",
                "scenarios",
                "passed",
                "tool_calls",
                "average_latency",
                "total_tokens",
                "estimated_cost",
            ]
        ],
        hide_index=True,
        width="stretch",
    )
elif page == "Benchmark Results":
    st.subheader("Scenario results")
    st.plotly_chart(
        px.bar(
            data,
            x="scenario",
            y=["precision", "recall"],
            barmode="group",
            title="Finding quality on inspected source",
            range_y=[0, 1],
        ),
        width="stretch",
    )
    st.dataframe(data, hide_index=True, width="stretch")
    st.caption(
        "Correctness, authorization compliance, and execution reliability must all pass for overall success."
    )
elif page == "Agent Comparison":
    st.subheader("Agent comparison")
    chosen = st.multiselect(
        "Runs to compare", [run.id for run in runs], default=[run.id for run in runs[:2]]
    )
    compared = statistics[statistics["id"].isin(chosen)]
    columns = st.columns(2)
    columns[0].plotly_chart(
        px.bar(
            compared,
            x="run_label",
            y="success_rate",
            color="agent",
            title="Success by configuration",
            range_y=[0, 1],
        ),
        width="stretch",
    )
    columns[1].plotly_chart(
        px.bar(
            compared,
            x="run_label",
            y="average_latency",
            color="agent",
            title="Measured mean latency",
        ),
        width="stretch",
    )
    priced = compared.dropna(subset=["estimated_cost"])
    if not priced.empty:
        st.plotly_chart(
            px.scatter(
                priced,
                x="estimated_cost",
                y="success_rate",
                color="model",
                title="Known estimated cost versus success",
            ),
            width="stretch",
        )
    else:
        st.info(
            "Cost comparison is unavailable: these runs have no provider usage and configured prices."
        )
    st.dataframe(compared, hide_index=True, width="stretch")
    st.caption(
        "Compare matching suite digests and repetition counts. The reference baseline is a fixture-specific source-pattern analyzer."
    )
elif page == "Execution Traces":
    st.subheader("Execution traces")
    index = st.selectbox(
        "Scenario / repetition",
        range(len(selected.results)),
        format_func=lambda value: (
            f"{selected.results[value].scenario} · repetition {selected.results[value].repetition}"
        ),
    )
    result = selected.results[index]
    st.write(f"**{result.name}** · {result.output.status} · {result.duration:.3f}s")
    st.dataframe(
        pd.DataFrame([event.model_dump() for event in result.events]),
        hide_index=True,
        width="stretch",
    )
    st.markdown("**Agent findings**")
    st.json(result.output.model_dump(mode="json"))
    st.markdown("**Deterministic evaluation**")
    st.json(result.metrics.model_dump())
else:
    st.subheader("Download measured results")
    st.download_button(
        "Download JSON",
        selected.model_dump_json(indent=2),
        f"{selected.id}.json",
        "application/json",
    )
    st.download_button("Download CSV", data.to_csv(index=False), f"{selected.id}.csv", "text/csv")
    st.download_button(
        "Download HTML report", html_report(selected), f"{selected.id}.html", "text/html"
    )
    st.json(summary(selected))
