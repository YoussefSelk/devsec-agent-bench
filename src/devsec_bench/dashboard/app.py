"""Dark, evidence-driven dashboard shell; benchmark business logic stays in the runner."""

import os
from pathlib import Path

import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from devsec_bench.benchmarks.loader import discover
from devsec_bench.benchmarks.runner import run_suite
from devsec_bench.dashboard import pages
from devsec_bench.dashboard.theme import apply_theme
from devsec_bench.models import AgentConfig, Run
from devsec_bench.reporting.exporters import export
from devsec_bench.storage.database import Database

VIEWS = [
    "Overview",
    "Benchmark Runs",
    "Scenarios",
    "Agent Comparison",
    "Execution Traces",
    "Reports",
    "Settings",
]
DESCRIPTIONS = {
    "Overview": "Security-agent performance, safety and operational cost across measured evaluations.",
    "Benchmark Runs": "Filter measured outcomes and inspect finding quality, execution failures and safety decisions.",
    "Scenarios": "Explore the authorized task catalog, repository permissions and reproducible evaluation criteria.",
    "Agent Comparison": "Compare observed quality, latency and available cost across agent configurations.",
    "Execution Traces": "Inspect chronological tool requests, authorization decisions and evaluation evidence.",
    "Reports": "Export sanitized, reproducible evidence from your evaluation history.",
    "Settings": "Configure offline execution defaults and inspect the local security boundary.",
}
ICONS = {
    "Overview": "◫",
    "Benchmark Runs": "▤",
    "Scenarios": "◇",
    "Agent Comparison": "⇄",
    "Execution Traces": "⌘",
    "Reports": "▥",
    "Settings": "⚙",
}

st.set_page_config(page_title="DevSec Agent Bench", layout="wide", initial_sidebar_state="auto")
apply_theme()
home = Path(os.environ.get("DEVSEC_BENCH_HOME", ".bench")).resolve()
database_path = home / "history.db"


@st.cache_data(show_spinner=False, max_entries=8)
def history(path: str, revision: int) -> list[Run]:
    database = Database(Path(path))
    try:
        return database.list_runs()
    finally:
        database.engine.dispose()


def read_history() -> list[Run]:
    revision = database_path.stat().st_mtime_ns if database_path.exists() else 0
    return history(str(database_path), revision)


with st.sidebar:
    st.markdown(
        '<div class="brand"><span class="brand-mark">DS</span><div><div class="brand-name">DevSec Agent Bench</div><div class="brand-subtitle">Evaluation workspace</div></div></div>',
        unsafe_allow_html=True,
    )
    requested = st.query_params.get("view", "Overview")
    if requested == "Benchmark Results":
        requested = "Benchmark Runs"
    page = st.radio(
        "Workspace",
        VIEWS,
        index=VIEWS.index(requested) if requested in VIEWS else 0,
        format_func=lambda item: f"{ICONS[item]}  {item}",
        label_visibility="collapsed",
    )
    st.divider()
    st.caption("LOCAL WORKSPACE")
    st.caption("Eight authorized synthetic scenarios. Read-only tools. No fixture execution.")
    if st.button("Refresh history", width="stretch"):
        history.clear()
    st.caption("v0.1.0 · SQLite history")
st.query_params["view"] = page

header, action = st.columns([4, 1.3])
with header:
    st.markdown(
        '<div class="eyebrow">DevSec Agent Bench / Evaluation workspace</div>',
        unsafe_allow_html=True,
    )
    st.title(page)
    st.caption(DESCRIPTIONS[page])
with action:
    with st.popover("Run Benchmark", type="primary", width="stretch"):
        st.markdown("**Offline reference evaluation**")
        st.caption("Analyze trusted synthetic sources. No API key or paid model call.")
        definitions = discover()
        with st.form("launch-benchmark"):
            target = st.selectbox(
                "Benchmark scope", ["All scenarios", *[scenario.id for scenario in definitions]]
            )
            repetitions = st.number_input("Repetitions", min_value=1, max_value=20, value=1)
            submitted = st.form_submit_button(
                "Start reference run", type="primary", width="stretch"
            )
        if submitted:
            defaults = st.session_state.get(
                "offline_defaults",
                {"max_iterations": 20, "timeout": 30.0, "concurrency": 2, "seed": 0},
            )
            config = AgentConfig(
                max_iterations=int(defaults["max_iterations"]),
                timeout=float(defaults["timeout"]),
                seed=int(defaults["seed"]),
            )
            scenarios = [
                scenario
                for scenario in definitions
                if target == "All scenarios" or scenario.id == target
            ]
            database: Database | None = None
            try:
                database = Database(database_path)
                with st.spinner("Evaluating authorized repositories…"):
                    result = run_suite(
                        scenarios,
                        config,
                        repetitions=int(repetitions),
                        concurrency=int(defaults["concurrency"]),
                        on_update=database.save,
                    )
                    export(result, home / "reports")
                st.session_state["launch_notice"] = (
                    f"Run {result.id[:8]} recorded: {sum(item.metrics.passed for item in result.results)}/{len(result.results)} passed."
                )
                history.clear()
                st.rerun()
            except (ValueError, OSError, SQLAlchemyError):
                st.error(
                    "The evaluation could not be completed. Check the configured history directory and execution limits."
                )
            finally:
                if database is not None:
                    database.engine.dispose()

if "launch_notice" in st.session_state:
    st.info(st.session_state.pop("launch_notice"))
try:
    runs = read_history()
except Exception:
    st.error("Evaluation history could not be read. Check the history file and its permissions.")
    st.stop()

selected: Run | None = None
if runs and page in {"Execution Traces", "Reports"}:
    selected = st.selectbox(
        "Evaluation run",
        runs,
        format_func=lambda run: (
            f"{run.id[:8]} · {run.config.model or 'Reference baseline'} · {run.timestamp[:19]} UTC"
        ),
    )

if page == "Overview":
    pages.overview(runs)
elif page == "Scenarios":
    pages.scenarios(runs)
elif page == "Settings":
    pages.settings(str(home))
elif not runs:
    st.info(
        "No recorded evaluations yet. Use Run Benchmark to create an offline reference baseline."
    )
elif page == "Benchmark Runs":
    pages.benchmark_runs(runs)
elif page == "Agent Comparison":
    pages.comparison(runs)
elif page == "Execution Traces" and selected:
    pages.traces(selected)
elif page == "Reports" and selected:
    pages.reports(selected)

st.divider()
st.caption(
    "Measured evidence only · Reference results are not LLM performance estimates · Secrets redacted in stored traces"
)
