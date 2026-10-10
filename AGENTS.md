# Development contract

Use Python 3.11+, read-only fixture analysis, and explicit tool allowlists.
Never execute fixture code. Never include ground truth in an agent context.
Never record credentials, raw provider errors, or tool file bodies in durable traces.
Keep scenario assets inside src/devsec_bench/scenarios so installed wheels work.
Run `ruff check .`, `ruff format --check .`, `mypy src`, and `pytest` before publishing.
Commit meaningful units with Conventional Commits. Do not commit runtime databases.
