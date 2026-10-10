# DevSec Agent Bench Implementation Plan

Execution: native, as requested by the user's autonomous implementation instructions.
Spec: docs/design.md and the user's supplied master task.

Global constraints: Python 3.11+, eight local synthetic scenarios, no fixture execution,
no fake measurements, read-only allowlisted tools, unknown cost/usage represented as null.

Review focus: symlink/canonical path escapes; ground-truth leakage; malformed provider
responses and unknown usage; failures within concurrent repetitions; interruption persistence.

1. Package and schemas: loader discover() -> list[Scenario], validated bounds and fixtures.
   Write/run loader and invalid-definition tests; implement and commit.
2. Tool boundary: Registry.call(name, args) -> JSON object and chronological ToolEvent.
   Write/run traversal, symlink, secret, read-only, output-bound tests; implement and commit.
3. Offline execution: ReferenceAgent.run(context, registry, config) -> AgentOutput;
   evaluate(expected, output, events) -> Metrics; run_suite() -> Run.
   Write/run deterministic, precision, recall, limits, and partial-failure tests; commit.
4. Storage/reporting: Database.save/run/latest/list; export(run, directory); compare(runs).
   Write/run round-trip, sanitization, report parse and CLI integration tests; commit.
5. Provider: chat request/response validation, tool loop, token/cost/budget accounting.
   Write/run local HTTP integration and missing credentials tests; implement and commit.
6. MCP: real SDK stdio server using Registry. Write/run protocol boundary test; commit.
7. Dashboard: actual persisted data, navigation, charts, traces and downloads.
   Run Streamlit AppTest and browser; commit real screenshot assets when possible.
8. Docker/CI/docs: restricted wrapper, fail-closed tests, build/run container,
   executable quality pipelines, final README. Run full quality suite and wheel smoke.
9. Review, fixes, GitHub creation/push, inspect remote Actions result; document evidence.
