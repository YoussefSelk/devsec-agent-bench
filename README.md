# DevSec Agent Bench

An open-source workbench for evaluating how security agents inspect authorized sample applications: what they found, what they did, and whether they respected permissions.

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-222321)](pyproject.toml)
[![MIT](https://img.shields.io/badge/license-MIT-8C3B32)](LICENSE)
[![Quality and offline benchmark](https://github.com/YoussefSelk/devsec-agent-bench/actions/workflows/ci.yml/badge.svg)](https://github.com/YoussefSelk/devsec-agent-bench/actions/workflows/ci.yml)

Eight synthetic repositories, seven bounded read-only tools, a separate structural evaluator, and actual SQLite execution history. Start with the offline reference agent; no account or credentials are required. An OpenAI provider adapter, MCP stdio server, CLI, restricted Docker execution, and CI reports support deeper evaluation.

![Evaluation runs](docs/assets/runs.png)

## Start an evaluation

Python 3.11 or newer, from a checkout:

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e '.[dev]'
devsec-bench dashboard --port 8517
```

Open the local address printed by Streamlit. Choose **New run**, select a benchmark, keep **Offline demo**, review permissions, and start. The first-run screen offers a single-scenario demonstration. Advanced limits stay collapsed until needed.

For locked dependencies, install [uv](https://docs.astral.sh/uv/) and use `uv sync --frozen --extra dev`, then prefix commands with `uv run --frozen`.

```bash
devsec-bench validate
devsec-bench run --agent reference
devsec-bench report --latest
devsec-bench compare RUN_ID_A RUN_ID_B
```

History lives in `.bench/history.db`; reports in `.bench/reports/`. `--home` belongs to each command. The offline suite passes eight known fixture checks; this demonstrates the harness, not general agent capability.

## Read the evidence

**Runs** is a searchable, filterable execution list. **Benchmarks** explains tasks and permissions. **Compare** aligns two recorded runs by scenario and repetition. **Documentation** explains results; Preferences sets session defaults.

Open a run to inspect:

- **Outcome:** plain-language result and separate finding, permission, and reliability checks.
- **Findings:** affected location, agent correction, verified evaluator expectation, and supporting evidence.
- **Agent actions:** chronological tool requests, permission decisions, durations, and expandable sanitized metadata.
- **Evidence:** exact matching rules, precision/recall, correction rubric, and raw evaluation JSON.
- **Timing & usage:** measured duration and provider-reported tokens/cost, with unknown values kept unavailable.

**Export & reproduce** provides JSON, CSV, HTML, configuration, fixture fingerprint, and a CLI recipe. Result URLs preserve the selected scenario, repetition, and inspection section. Reference answers appear only after execution and only when current fixtures match the recorded fingerprint; agents never receive them.

<details>
<summary>Real application screenshots</summary>

### New evaluation

![Permission review](docs/assets/new-evaluation.png)

### Run details

![Outcome inspection](docs/assets/run-details.png)

### Findings

![Finding and correction evidence](docs/assets/findings.png)

### Agent actions

![Chronological execution trace](docs/assets/execution-trace.png)

### Comparison

![Aligned run comparison](docs/assets/comparison.png)

</details>

## Design and architecture

A light editorial workbench puts execution and inspection ahead of charts. Warm neutrals, restrained red, strong text hierarchy, flat rows, and progressive disclosure support both first-time users and technical investigation. Four task destinations replace the previous dashboard categories and permanent sidebar.

The frontend remains Streamlit: native labeled controls and responsive columns provide the required workflows with a small CSS foundation and no extra backend or JavaScript framework. The Python runner, evaluator, permission registry, database, CLI, and MCP protocol remain independent of presentation.

See the [research rationale](docs/product-design.md), [design system](docs/design-system.md), [technical reference](docs/reference.md), and [verification evidence](docs/verification.md).

## Contribute

```bash
uv sync --frozen --extra dev
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv run --frozen mypy src
uv run --frozen pytest
uv build
```

Follow [AGENTS.md](AGENTS.md). Add only small authorized synthetic fixtures, keep expected answers out of agent context, preserve permission checks, and report actual measurements. GitHub Actions verifies Python 3.11/3.12; [GitLab CI](.gitlab-ci.yml) provides quality and benchmark artifact jobs.

## Limits

This is an evaluation harness, not a production vulnerability scanner. The reference agent recognizes fixture patterns; eight single-finding tasks are not a representative security benchmark. Correction scoring checks a structured action and text length, not patch safety. Tool bodies and private reasoning are not retained. Paid provider compatibility requires your credentials and model; no paid request or hosted GitLab pipeline is claimed in the verification record. See the [technical boundaries](docs/reference.md) before extending execution to other agents.

[MIT license](LICENSE).
