import csv
import html
import json
from pathlib import Path
from typing import Any
from xml.etree.ElementTree import Element, SubElement, tostring

from devsec_bench.evaluation.comparison import summary
from devsec_bench.models import Run
from devsec_bench.storage.database import sanitized_run


def rows(run: Run) -> list[dict[str, Any]]:
    return [{"run_id": run.id, "scenario": r.scenario, "name": r.name, "repetition": r.repetition, "passed": r.metrics.passed, "correctness": r.metrics.correctness, "safe": r.metrics.safe, "status": r.output.status, "precision": r.metrics.precision, "recall": r.metrics.recall, "false_positives": r.metrics.false_positives, "false_negatives": r.metrics.false_negatives, "location_accuracy": r.metrics.location_accuracy, "remediation_validity": r.metrics.remediation_validity, "policy_violations": r.metrics.policy_violations, "tool_calls": len(r.events), "duration": r.duration, **r.output.usage.model_dump(), "estimated_cost": r.estimated_cost} for r in run.results]


def html_report(run: Run) -> str:
    run = sanitized_run(run)
    stats = summary(run)
    table_rows = rows(run)
    columns = list(table_rows[0]) if table_rows else []

    def escape(value: Any) -> str:
        return html.escape("unavailable" if value is None else str(value))

    header = "".join(f"<th>{escape(c)}</th>" for c in columns)
    body = "".join("<tr>" + "".join(f"<td>{escape(row[c])}</td>" for c in columns) + "</tr>" for row in table_rows)
    details = "".join(f"<details><summary>{escape(r.scenario)} findings and trace</summary><pre>{escape(r.output.model_dump_json(indent=2))}</pre><pre>{escape(json.dumps([e.model_dump() for e in r.events], indent=2))}</pre></details>" for r in run.results)
    return f'<!doctype html><html lang="en"><meta charset="utf-8"><title>DevSec Agent Bench</title><style>body{{font:15px system-ui;margin:3rem;color:#183047;background:#f5f7fa}}table{{border-collapse:collapse;font-size:12px;display:block;overflow:auto}}th,td{{padding:10px;border-bottom:1px solid #cdd5df;text-align:left}}pre{{white-space:pre-wrap}}details{{margin:1rem 0}}</style><h1>DevSec Agent Bench</h1><p>{escape(run.config.agent)} agent • {escape(run.timestamp)} • Run {escape(run.id)}</p><p>Passed {stats["passed"]}/{stats["scenarios"]} • Success {stats["success_rate"]:.1%} • Policy violations {stats["policy_violations"]} • Cost USD {escape(stats["estimated_cost"])}</p><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table>{details}<p>Remediation scores validate structured action and minimum explanation length; they are not proof of semantic safety.</p></html>'


def export(run: Run, directory: Path) -> dict[str, Path]:
    run = sanitized_run(run)
    directory.mkdir(parents=True, exist_ok=True)
    paths = {kind: directory / f"{run.id}.{suffix}" for kind, suffix in {"json": "json", "csv": "csv", "html": "html", "junit": "xml"}.items()}
    paths["json"].write_text(run.model_dump_json(indent=2), encoding="utf-8")
    data = rows(run)
    with paths["csv"].open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(data[0]) if data else ["run_id"])
        writer.writeheader()
        writer.writerows(data)
    paths["html"].write_text(html_report(run), encoding="utf-8")
    failed = sum(not r.metrics.passed for r in run.results)
    suite = Element("testsuite", name="devsec-bench", tests=str(len(run.results)), failures=str(failed), time=str(sum(r.duration for r in run.results)))
    for result in run.results:
        case = SubElement(suite, "testcase", classname=result.scenario, name=f"repetition-{result.repetition}", time=str(result.duration))
        if not result.metrics.passed:
            SubElement(case, "failure", message=result.output.error or "Evaluation criteria failed").text = result.metrics.model_dump_json()
    if run.interrupted:
        SubElement(suite, "error", message="Benchmark interrupted; partial results preserved")
    paths["junit"].write_bytes(tostring(suite, encoding="utf-8", xml_declaration=True))
    return paths
