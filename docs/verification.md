# Verification record

Evidence is from local execution on 2026-10-10, not simulated output.

- Python 3.11 virtual environment and installed wheel both executed all eight reference scenarios.
- Ruff lint/format and strict mypy check the application; intentionally vulnerable sources are excluded.
- Pytest includes real MCP stdio, SQLite, report, CLI, local HTTP and Streamlit AppTest boundaries.
- Docker production image built; restricted no-network/read-only/non-root execution passed 8/8.
- An independent review produced regressions for interruption persistence, trace key redaction,
  incomplete-run dashboard views, absolute HTTP deadlines and quoted JSON secret redaction.
- Five dashboard images show actual reference results; CLI output is captured as text because
  native terminal screenshot capture was unavailable.
- No OpenAI API credential is configured: paid model compatibility has not been remotely verified.
- Hosted GitLab CI has not been run; its quality/benchmark commands are exercised locally.

Local final verification:

- Windows Python 3.11: **57 passed, 1 skipped** (OS denied symlink creation).
- Linux Python 3.11 in the read-only, no-network development container: **58 passed**,
  including the real symlink escape case. No test was skipped.
- `ruff check .`, `ruff format --check .`, `mypy src`: passed.
- Source distribution/wheel build: passed; a fresh non-editable wheel environment ran 8/8.
- Restricted production image: built and ran 8/8 with zero policy violations.
- CLI init/list/validate/run/report/compare are exercised by actual integration tests.
- Dashboard redesign: seven views, actual offline launch, filtered failure results,
  session execution settings, unreadable-history error/launch states, and weighted
  metrics verified against SQLite records. Browser inspection covered desktop,
  1024-pixel laptop and 768-pixel tablet layouts with collapsible navigation.
- The actual UI-launched run passed 8/8; its overview showed 25 total historical
  scenario attempts and 96% success (one earlier intentionally budget-limited failure).

GitHub Actions evidence is added after the repository's first hosted workflow finishes.
