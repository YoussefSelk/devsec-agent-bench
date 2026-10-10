# Design and acceptance contract

The user's master task is the specification. This document pins implementation choices.

A Pydantic domain layer separates public task context, findings, ground truth, usage,
tool events, scenario results, and run snapshots. YAML definitions and immutable
synthetic source repositories ship in the wheel. A loader validates containment and
ground truth before execution. The runner copies only repository sources into a
temporary directory for each scenario/repetition, never executes them, and evaluates
structured findings outside the agent. A thread pool schedules independent analyses.

A policy-controlled registry supplies seven bounded read-only tools. Paths are
relative, canonical, non-symlink, and repository scoped; secret paths and binary files
are denied. No shell, filesystem writes, arbitrary regex, or network tool exists.
The official MCP SDK exposes the same registry over stdio. Durable events retain
authorization and output-size metadata, never repository bodies or raw credentials.

The reference agent uses explicit source patterns on eight synthetic applications.
It is a limited deterministic baseline, not an LLM. A provider interface supports
documented OpenAI Chat Completions tool calling through httpx; credentials are read
only by the provider. Model and pricing are caller configuration. Unknown usage and
cost remain null. Dollar budgets require configured pricing and pre-request token
reservations. Loop, output-token, tool, and wall-clock budgets are enforced.

Evaluation matches unique category/file/line findings and structured remediation
actions against evaluator-only ground truth; stable finding identifiers are assigned
by the evaluator. Precision, recall, location, remediation, safety, reliability,
tokens, and costs remain distinct. Duplicate findings are false positives. Any denied
tool call prevents overall success, even if correctness passes.

SQLite uses relational runs, scenario results, and events. Reports emit sanitized
JSON, CSV, HTML, and JUnit. Streamlit reads the same stored runs and Plotly charts.
Docker execution uses a fixed image/command, no network in reference mode, non-root,
read-only root, capped resources, and a single artifact mount; Docker availability
is required when container isolation is requested. Local execution only reads trusted
synthetic fixtures; it does not claim to sandbox hostile Python plugins.

Validation covers negative paths as well as real CLI, MCP stdio, SQLite, exports,
wheel installation, and Docker. Remote LLM, CI, and publication success must be
reported only when directly verified. Screenshots must show actual application data.
