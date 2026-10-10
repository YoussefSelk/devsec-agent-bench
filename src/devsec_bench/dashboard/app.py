"""Editorial, task-oriented evaluation workbench over the existing benchmark engine."""

import os
from pathlib import Path

import streamlit as st

from devsec_bench.dashboard import inspection, pages, wizard
from devsec_bench.dashboard.theme import apply_theme
from devsec_bench.models import Run
from devsec_bench.storage.database import Database

NAVIGATION = ["Runs", "Benchmarks", "Compare", "Documentation"]
ALIASES = {
    "Overview": "Runs",
    "Benchmark Runs": "Runs",
    "Benchmark Results": "Runs",
    "Scenarios": "Benchmarks",
    "Agent Comparison": "Compare",
    "Execution Traces": "Runs",
    "Reports": "Runs",
    "Settings": "Documentation",
}

st.set_page_config(page_title="DevSec Agent Bench", layout="wide")
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


if "_navigate" in st.session_state:
    destination = st.session_state.pop("_navigate")
    st.query_params.clear()
    for key, item in destination.items():
        if item is not None:
            st.query_params[key] = str(item)
    base = destination["view"] if destination["view"] in NAVIGATION else "Runs"
    st.session_state["primary_nav"] = base
    st.session_state["_last_nav"] = base

requested = st.query_params.get("view", "Runs")
page = ALIASES.get(requested, requested)
if page not in [*NAVIGATION, "New run"]:
    page = "Runs"
base = page if page in NAVIGATION else "Runs"
if st.session_state.get("_route_view") != page:
    st.session_state["primary_nav"] = base
    st.session_state["_last_nav"] = base
st.session_state["_route_view"] = page
st.session_state.setdefault("_last_nav", base)
brand, utility = st.columns([5, 1.2])
brand.markdown('<div class="wordmark">DEVSEC<span>AGENT BENCH</span></div>', unsafe_allow_html=True)
with utility:
    pages.preferences(home)
nav = st.radio(
    "Navigation",
    NAVIGATION,
    horizontal=True,
    index=NAVIGATION.index(base),
    key="primary_nav",
    label_visibility="collapsed",
)
if nav != st.session_state["_last_nav"]:
    st.session_state["_last_nav"] = nav
    st.query_params.clear()
    st.query_params["view"] = nav
    st.rerun()
st.divider()

history_available = True
try:
    revision = database_path.stat().st_mtime_ns if database_path.exists() else 0
    runs = history(str(database_path), revision)
except Exception:
    runs = []
    history_available = False
    st.error(
        "Evaluation history could not be read. Check the file and its permissions; existing data has not been changed. New evaluations also require a valid writable history directory."
    )

if "launch_notice" in st.session_state:
    st.success(st.session_state.pop("launch_notice"))
if page == "New run":
    wizard.render(home, history.clear)
elif page == "Runs":
    run_id = st.query_params.get("run")
    selected = next((run for run in runs if run.id == run_id), None)
    if run_id and selected is None:
        st.warning("That run is not in this workspace. Browse the recorded runs below.")
    if selected:
        inspection.render(selected)
    else:
        pages.runs_index(runs, history_available=history_available)
elif page == "Benchmarks":
    pages.benchmarks()
elif page == "Compare":
    pages.comparison(runs)
else:
    pages.documentation()

st.divider()
st.caption(
    "Local evaluation workbench · Synthetic repositories only · Recorded evidence, never simulated results"
)
