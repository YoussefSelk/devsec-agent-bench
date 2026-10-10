"""Plain-language result inspection with progressively disclosed technical evidence."""

import shlex

import pandas as pd
import streamlit as st

from devsec_bench.benchmarks.loader import discover
from devsec_bench.dashboard.navigation import go
from devsec_bench.dashboard.theme import status_badge, value
from devsec_bench.dashboard.views import current_fixtures_match, run_rows, status_label
from devsec_bench.evaluation.comparison import summary
from devsec_bench.models import Run, ScenarioResult
from devsec_bench.reporting.exporters import html_report, rows

SECTIONS = ["Outcome", "Findings", "Agent actions", "Evidence", "Timing & usage"]


def explanation(result: ScenarioResult) -> str:
    if result.metrics.policy_violations:
        return "The agent requested access outside its permitted tools or repository. This result fails the safety check, even if its findings were correct."
    if result.output.status == "budget":
        return "The agent reached its iteration limit or another execution budget before finishing. Review Agent actions to see how far it got, then adjust the limit or investigate repeated tool calls."
    if result.output.status == "timeout":
        return (
            "The evaluation stopped at its time limit. Any completed actions are preserved below."
        )
    if result.output.status == "error":
        return "Execution failed before a reliable result was returned. The sanitized error and completed actions are available below."
    if result.metrics.passed:
        return "The agent found the expected issue, cited the correct location, passed the structured correction rubric and respected tool permissions."
    return "The response did not satisfy every benchmark check. Review missing findings, unexpected findings and the correction rubric under Evidence."


def actions(result: ScenarioResult) -> None:
    st.subheader("Observed agent actions")
    st.caption(
        "Chronological tool requests. Response bodies and private reasoning are not retained; the actual permission decision and response metadata are available."
    )
    if not result.events:
        st.info("No tools were called before this execution stopped.")
    for event in result.events:
        decision = "Allowed" if event.authorized else "Denied"
        with st.expander(
            f"{event.sequence:02} · {event.timestamp[11:19]} UTC · {event.tool} · {decision} · {event.duration * 1000:.1f} ms"
        ):
            st.write(f"**Permission decision: {decision}.** The agent requested `{event.tool}`.")
            st.write(f"Returned {event.bytes_returned} bytes in {event.duration * 1000:.1f} ms.")
            if event.error:
                st.error(event.error)
            st.json(event.model_dump(mode="json"), expanded=True)


def findings(run: Run, result: ScenarioResult) -> None:
    st.subheader("What the agent found")
    definitions = discover()
    verified = current_fixtures_match(run, definitions)
    definition = next(
        (scenario for scenario in definitions if verified and scenario.id == result.scenario), None
    )
    if not verified:
        st.warning(
            "Current fixture answers cannot be verified against this run's recorded fingerprint. Reference answers are hidden; recorded findings and evaluation metrics remain available."
        )
    st.write(f"**Recorded benchmark evaluation:** {status_label(result)}")
    if not result.output.findings:
        st.info(
            "No findings were returned. This does not mean the application is safe; check the execution outcome and expected benchmark checks."
        )
    for index, finding in enumerate(result.output.findings, 1):
        st.markdown(f"### {index}. {finding.category.replace('_', ' ').capitalize()}")
        st.write(finding.explanation)
        st.caption("Affected file and reported line")
        st.code(f"{finding.file}:{finding.line}", language="text")
        expected = (
            next(
                (
                    item
                    for item in definition.expected
                    if item.category == finding.category and item.file == finding.file
                ),
                None,
            )
            if definition
            else None
        )
        left, right = st.columns(2)
        with left:
            st.markdown("**Agent's suggested correction**")
            st.write(finding.remediation)
        with right:
            st.markdown("**Evaluation expectation**")
            st.write(
                expected.reference
                if expected
                else "Reference answer unavailable or no matching expected finding."
            )
        st.caption(
            "Supporting location evidence: "
            + (
                f"expected {expected.file}:{expected.line}; reported {finding.file}:{finding.line}."
                if expected
                else "no verified reference location is available for this finding."
            )
        )
        with st.expander(f"Technical finding {index}"):
            st.json(finding.model_dump(), expanded=True)
            if expected:
                st.json(expected.model_dump(), expanded=False)
        st.divider()
    if definition:
        with st.expander("Expected benchmark checks (evaluator only)"):
            st.caption(
                "These answers are shown for result inspection. They are never passed into the agent's task context."
            )
            st.json([item.model_dump() for item in definition.expected], expanded=False)


def evidence(result: ScenarioResult) -> None:
    st.subheader("How this result was evaluated")
    measures = [
        (
            "Expected findings matched",
            result.metrics.true_positives,
            "Unique category, file and exact line matches",
        ),
        (
            "Unexpected findings",
            result.metrics.false_positives,
            "Unmatched or duplicate reported findings",
        ),
        (
            "Expected findings missed",
            result.metrics.false_negatives,
            "Ground-truth checks without a match",
        ),
        (
            "Precision",
            value(result.metrics.precision, "percent"),
            "Matched findings / reported findings",
        ),
        ("Recall", value(result.metrics.recall, "percent"), "Matched findings / expected findings"),
        (
            "Correction rubric",
            value(result.metrics.remediation_validity, "percent"),
            "Expected action plus minimum correction text length",
        ),
        ("Permission violations", result.metrics.policy_violations, "Denied tool requests"),
    ]
    for label, measured, meaning in measures:
        st.write(f"**{label}: {measured}**")
        st.caption(meaning)
    st.caption(
        "Correctness, permission compliance and execution reliability must all pass. Correction scoring is structural; it is not proof that an arbitrary patch is safe."
    )
    with st.expander("Raw evaluation JSON"):
        st.json(result.metrics.model_dump(), expanded=True)


def timing(run: Run, result: ScenarioResult) -> None:
    st.subheader("Timing and available usage")
    data = {
        "Agent": "Offline demo" if run.config.agent == "reference" else "LLM agent",
        "Provider": "Offline" if run.config.agent == "reference" else run.config.provider,
        "Model": run.config.model or "Reference source-pattern implementation",
        "Scenario duration": value(result.duration, "seconds"),
        "Tool calls": len(result.events),
        "Input tokens": value(result.output.usage.input_tokens),
        "Output tokens": value(result.output.usage.output_tokens),
        "Total tokens": value(result.output.usage.total_tokens),
        "Estimated cost": value(result.estimated_cost, "cost"),
        "Recorded (UTC)": run.timestamp,
    }
    for label, measured in data.items():
        st.write(f"**{label}:** {measured}")
    st.caption(
        "Duration includes workspace preparation and analysis. Missing usage or pricing stays unavailable; the offline demo makes no model request."
    )


def render(run: Run) -> None:
    if st.button("Back to runs", type="tertiary"):
        go("Runs")
    st.title(f"Run {run.id[:8]}")
    st.caption(f"{run.config.model or 'Offline demo'} · {run.timestamp[:19].replace('T', ' ')} UTC")
    status_badge(str(run_rows([run])[0]["Outcome"]))
    with st.popover("Export & reproduce"):
        st.download_button(
            "Download run JSON", run.model_dump_json(indent=2), f"{run.id}.json", "application/json"
        )
        st.download_button(
            "Download results CSV",
            pd.DataFrame(rows(run)).to_csv(index=False),
            f"{run.id}.csv",
            "text/csv",
        )
        st.download_button("Download HTML report", html_report(run), f"{run.id}.html", "text/html")
        repetitions = max((result.repetition for result in run.results), default=1)
        command = [
            "devsec-bench",
            "run",
            "--agent",
            run.config.agent,
            "--max-iterations",
            str(run.config.max_iterations),
            "--timeout",
            str(run.config.timeout),
            "--request-timeout",
            str(run.config.request_timeout),
            "--seed",
            str(run.config.seed),
            "--repetitions",
            str(repetitions),
        ]
        if run.config.model:
            command += ["--model", run.config.model]
        ids = {result.scenario for result in run.results}
        if len(ids) == 1:
            command += ["--scenario", next(iter(ids))]
        st.caption(
            "POSIX reproduction command for the observed scope. Pricing/budget files must be supplied separately for paid runs; partial runs may have missing attempts."
        )
        st.code(shlex.join(command), language="bash", wrap_lines=True)
        with st.expander("Configuration and fixture fingerprint"):
            st.json(run.config.model_dump(mode="json"), expanded=False)
            st.code(run.suite_digest or "Unavailable", language="text")
    st.divider()
    if not run.results:
        st.info(
            "This snapshot has no completed benchmark results. The run may still be starting or may have been interrupted."
        )
        return
    requested_result = (st.query_params.get("scenario"), st.query_params.get("repetition", "1"))
    result_key = f"result_{run.id}"
    if st.session_state.get(f"_result_url_{run.id}") != requested_result:
        selected = next(
            (
                item
                for item in run.results
                if (item.scenario, str(item.repetition)) == requested_result
            ),
            run.results[0],
        )
        st.session_state[result_key] = selected
    result = st.selectbox(
        "Benchmark result",
        run.results,
        format_func=lambda item: f"{item.scenario} · {item.name} · repetition {item.repetition}",
        key=result_key,
    )
    st.query_params["scenario"] = result.scenario
    st.query_params["repetition"] = str(result.repetition)
    st.session_state[f"_result_url_{run.id}"] = (result.scenario, str(result.repetition))
    requested = st.query_params.get("section", "Outcome")
    if st.session_state.get(f"_section_url_{run.id}") != requested:
        st.session_state[f"inspect_{run.id}"] = requested if requested in SECTIONS else "Outcome"
    section = st.radio(
        "Inspect",
        SECTIONS,
        horizontal=True,
        index=SECTIONS.index(requested) if requested in SECTIONS else 0,
        key=f"inspect_{run.id}",
    )
    st.query_params["section"] = section
    st.session_state[f"_section_url_{run.id}"] = section
    st.divider()
    if section == "Outcome":
        st.subheader(status_label(result))
        st.write(explanation(result))
        st.write(
            f"**{summary(run)['passed']}/{len(run.results)} benchmark results passed** in this recorded run."
        )
        if result.output.error:
            st.error(result.output.error)
        for label, passed in [
            ("Finding checks", result.metrics.correctness),
            ("Tool permissions", result.metrics.safe),
            ("Execution reliability", result.metrics.reliable),
        ]:
            st.write(f"**{label}:** {'Passed' if passed else 'Failed'}")
        st.caption(
            "Start with Findings for the issue and correction; use Agent actions to understand execution or permission failures."
        )
    elif section == "Findings":
        findings(run, result)
    elif section == "Agent actions":
        actions(result)
    elif section == "Evidence":
        evidence(result)
    else:
        timing(run, result)
