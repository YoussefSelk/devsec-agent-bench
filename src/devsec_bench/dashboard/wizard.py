"""Guided evaluation flow; existing runner remains the sole execution engine."""

import json
import os
from collections.abc import Callable
from pathlib import Path

import streamlit as st
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from devsec_bench.benchmarks.loader import discover
from devsec_bench.benchmarks.runner import run_suite
from devsec_bench.dashboard.navigation import go
from devsec_bench.models import AgentConfig, Pricing
from devsec_bench.reporting.exporters import export
from devsec_bench.storage.database import Database


def render(home: Path, refresh: Callable[[], None]) -> None:
    st.title("New evaluation")
    st.caption("Choose a task, choose an agent, then review what it is allowed to do.")
    step = int(st.session_state.get("wizard_step", 0))
    draft = st.session_state.setdefault(
        "draft_run", {"scope": "All scenarios", "agent": "Offline demo", "model": ""}
    )
    st.markdown("**1. Benchmark**  /  **2. Agent**  /  **3. Permissions**  /  **4. Evaluate**")
    st.divider()
    definitions = discover()

    def change(next_step: int) -> None:
        st.session_state["wizard_step"] = next_step
        st.rerun()

    if step == 0:
        st.subheader("What would you like to test?")
        choices = ["All scenarios", *[scenario.id for scenario in definitions]]
        st.session_state.setdefault("wizard_scope", draft["scope"])
        draft["scope"] = st.selectbox(
            "Choose a benchmark",
            choices,
            key="wizard_scope",
            format_func=lambda key: (
                "Full suite · 8 synthetic applications"
                if key == "All scenarios"
                else next(
                    f"{scenario.id} · {scenario.name}"
                    for scenario in definitions
                    if scenario.id == key
                )
            ),
        )
        st.write(
            "The full suite checks eight small applications with deliberately introduced security mistakes. Nothing is executed or changed."
        )
        if draft["scope"] != "All scenarios":
            selected = next(scenario for scenario in definitions if scenario.id == draft["scope"])
            st.write(selected.description)
        if st.button("Continue", type="primary"):
            change(1)
    elif step == 1:
        st.subheader("Who should review the application?")
        st.session_state.setdefault("wizard_agent", draft["agent"])
        draft["agent"] = st.radio(
            "Choose an agent",
            ["Offline demo", "LLM agent"],
            key="wizard_agent",
        )
        if draft["agent"] == "Offline demo":
            st.write(
                "Start without an account or credentials. The demo reads the actual sample files and produces inspectable results. It recognizes known fixture patterns; it is a reference implementation, not an LLM."
            )
        else:
            st.write(
                "Use OpenAI's tool-calling API. The model name is supplied by you, and paid calls use your provider account."
            )
            st.session_state.setdefault("wizard_model", draft.get("model", ""))
            draft["model"] = st.text_input(
                "Model identifier",
                key="wizard_model",
                placeholder="Your available model identifier",
            )
            if not os.environ.get("OPENAI_API_KEY"):
                st.info(
                    "Provider credentials are unavailable. Set OPENAI_API_KEY in the application environment, or choose Offline demo to continue without credentials."
                )
        back, forward = st.columns(2)
        if back.button("Back"):
            change(0)
        if forward.button(
            "Review permissions",
            type="primary",
            disabled=draft["agent"] == "LLM agent" and not draft["model"].strip(),
        ):
            change(2)
    else:
        selected_definitions = [
            scenario
            for scenario in definitions
            if draft["scope"] == "All scenarios" or scenario.id == draft["scope"]
        ]
        st.subheader("Review before you start")
        st.write(
            f"**Benchmark:** {draft['scope']} · {len(selected_definitions)} authorized repositories"
        )
        st.write(
            f"**Agent:** {draft['agent']}"
            + (f" · {draft['model']}" if draft["agent"] == "LLM agent" else "")
        )
        st.markdown(
            "**Permitted:** read sample files, search source text, inspect local manifests and pinned dependency advisories."
        )
        st.markdown(
            "**Not permitted:** changing files, running commands, reading private or secret files, accessing another repository, or making network requests through tools."
        )
        st.caption(
            "Tools enforce these permissions independently of the agent. Repository copies are isolated from the original fixtures."
        )
        defaults = st.session_state.get(
            "offline_defaults", {"max_iterations": 20, "timeout": 30.0, "concurrency": 1, "seed": 0}
        )
        price: Pricing | None = None
        max_cost: float | None = None
        valid = True
        with st.expander("Advanced execution settings"):
            columns = st.columns(2)
            iterations = columns[0].number_input(
                "Maximum iterations",
                min_value=1,
                max_value=100,
                value=int(defaults["max_iterations"]),
            )
            timeout = columns[1].number_input(
                "Time limit per scenario (seconds)",
                min_value=1.0,
                max_value=600.0,
                value=float(defaults["timeout"]),
            )
            concurrency = columns[0].number_input(
                "Concurrent workers", min_value=1, max_value=32, value=int(defaults["concurrency"])
            )
            repetitions = columns[1].number_input("Repetitions", min_value=1, max_value=20, value=1)
            seed = columns[0].number_input(
                "Scheduling seed", min_value=0, max_value=2**31 - 1, value=int(defaults["seed"])
            )
            st.caption(
                "Benchmark-defined time and iteration limits still apply when lower than these requested limits."
            )
            if draft["agent"] == "LLM agent":
                uploaded = st.file_uploader("Model pricing JSON (optional)", type=["json"])
                if uploaded:
                    try:
                        if uploaded.size > 32768:
                            raise ValueError
                        prices = json.loads(uploaded.getvalue())
                        price = Pricing.model_validate(prices[draft["model"]])
                    except (ValueError, KeyError, TypeError, ValidationError):
                        valid = False
                        st.error(
                            "Pricing must map this model identifier to input_per_million, output_per_million, source and timestamp."
                        )
                if st.checkbox("Enforce a dollar reservation budget"):
                    max_cost = st.number_input(
                        "Maximum estimated cost (USD)", min_value=0.0, value=0.10, step=0.01
                    )
                    if (
                        price is None
                        or len(selected_definitions) != 1
                        or repetitions != 1
                        or concurrency != 1
                    ):
                        valid = False
                        st.warning(
                            "A dollar-capped run requires model pricing, one benchmark, one repetition and one worker."
                        )
                if price is None:
                    st.caption(
                        "Estimated cost will be unavailable without pricing and reported usage."
                    )
        st.write(
            f"**Requested limits:** {iterations} iterations · {timeout:g}s per scenario · {concurrency} worker(s)"
        )
        if draft["agent"] == "LLM agent" and not os.environ.get("OPENAI_API_KEY"):
            valid = False
            st.info(
                "Provider credentials are unavailable. Return to Agent and choose Offline demo, or restart the application with OPENAI_API_KEY configured."
            )
        back, start = st.columns(2)
        if back.button("Back"):
            change(1)
        if start.button("Start evaluation", type="primary", disabled=not valid):
            database: Database | None = None
            try:
                config = AgentConfig(
                    agent="reference" if draft["agent"] == "Offline demo" else "llm",
                    model=draft["model"] if draft["agent"] == "LLM agent" else None,
                    max_iterations=int(iterations),
                    timeout=float(timeout),
                    seed=int(seed),
                    pricing=price,
                    max_cost=max_cost,
                )
                database = Database(home / "history.db")
                with st.spinner(
                    "Evaluating authorized sample repositories. Completed results are saved as they finish."
                ):
                    result = run_suite(
                        selected_definitions,
                        config,
                        repetitions=int(repetitions),
                        concurrency=int(concurrency),
                        on_update=database.save,
                    )
                    export(result, home / "reports")
                refresh()
                st.session_state["launch_notice"] = (
                    "Evaluation recorded. Inspect the outcome and its supporting evidence below."
                )
                go("Runs", result.id, "Outcome")
            except (ValueError, OSError, SQLAlchemyError):
                st.error(
                    "Evaluation could not be started or saved. Check credentials, execution settings and the history directory. Existing history was preserved."
                )
            finally:
                if database is not None:
                    database.engine.dispose()
    if st.button("Cancel evaluation", type="tertiary"):
        go("Runs")
