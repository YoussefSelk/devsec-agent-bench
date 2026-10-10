"""Bookmarkable task navigation without custom browser state or JavaScript."""

import streamlit as st


def go(
    view: str,
    run_id: str | None = None,
    section: str | None = None,
    scenario: str | None = None,
    repetition: int | None = None,
) -> None:
    st.session_state["_navigate"] = {
        "view": view,
        "run": run_id,
        "section": section,
        "scenario": scenario,
        "repetition": repetition,
    }
    st.rerun()


def new_run(scope: str = "All scenarios") -> None:
    st.session_state["draft_run"] = {"scope": scope, "agent": "Offline demo", "model": ""}
    st.session_state["wizard_step"] = 0
    st.session_state["wizard_scope"] = scope
    st.session_state["wizard_agent"] = "Offline demo"
    st.session_state["wizard_model"] = ""
    go("New run")
