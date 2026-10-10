# Verification record

Evidence comes from actual execution on 2026-10-10. Screenshots show the running
application and recorded synthetic evaluations, not mockups.

## Automated and engine verification

- Windows Python 3.11 full suite: **64 passed, 1 skipped**; the OS denied symlink creation.
- Read-only, no-network Linux development container: **65 passed**, including symlink denial.
- Latest history-error refinement: all **10 dashboard tests** passed; lint, formatting and strict mypy passed.
- Hosted [GitHub Actions for implementation commit 71407fb](https://github.com/YoussefSelk/devsec-agent-bench/actions/runs/38079619917):
  both Python **3.11 and 3.12 jobs succeeded**, including quality, tests, packaging,
  fixture validation, offline execution, reports and an installed-wheel smoke test.
- Local source distribution and wheel build succeeded. The non-editable installed wheel
  executed **8/8** reference scenarios with zero permission violations.
- Production Docker image built. Restricted reference execution passed **8/8** with
  read-only root, no network, non-root identity, dropped capabilities and bounded resources.
- Real integration tests cover official MCP stdio, local HTTP provider exchange/deadlines,
  SQLite persistence, reports, CLI, repetition/concurrency, interruption, permission denial,
  secret/traversal/symlink boundaries and missing usage accounting.

An independent product review found route synchronization, historical reference evidence,
unknown comparison fingerprints and incomplete evidence URLs. Fixes preserve navigation
state, verify current fixture answers, warn about unknown compatibility, and retain
scenario/repetition/section bookmarks. Comparison JSON includes aligned scenario rows.

## Actual user journeys

| Journey | Evidence |
|---|---|
| First-time offline demo | Browser: empty isolated history → SEC-001 → Offline demo → permission review → actual successful run `3d501908`; AppTest also launches the full 8/8 suite |
| Find and read a completed evaluation | Browser opens recorded run `9bc2e8f0`; outcome separates finding checks, permissions and reliability |
| Explain failure | Actual iteration-limited run `1ad9be2f`: budget exhausted, preserved actions, failed reliability, passed permissions |
| Inspect a tool decision | Browser expands the recorded `list_files` authorization metadata; AppTest additionally runs a real forbidden traversal request and inspects its Denied event |
| Compare and export | Browser compares compatible 8-scenario runs `9bc2e8f0` and `7047336f`, downloads CSV, and verifies eight aligned rows against recorded outcomes |

Search/outcome filters, navigation, unavailable credentials with offline recovery,
pending runs, bookmarked scenario/section context, corrupt-history preservation,
missing comparison results and changed-fixture answer suppression are automated regressions.

## Visual and accessibility review

Inspected first-run, Runs, wizard, outcome, findings, chronological actions, comparison,
failed evaluation and unreadable-history states. Desktop is **1440px**, laptop **1024px**,
mobile **390px**. Viewport dimensions were checked against the actual DOM; mobile page
width stayed 390px. Native columns stack, navigation wraps and supporting text remains readable.

Browser inspection discovered faded caption opacity and changed native form wrappers;
both were corrected. Measured text/status tokens meet AA contrast, control borders meet
3:1, labels and status words are explicit, and a real Tab action showed a 2px accent
focus outline. This is a practical accessibility review, not a screen-reader certification.

Six README screenshots: `runs.png`, `new-evaluation.png`, `run-details.png`, `findings.png`,
`execution-trace.png`, `comparison.png`. Additional evidence covers first-run, laptop/mobile
comparison, mobile wizard/failure and corrupt history. CLI output is preserved as actual
text in `assets/cli-benchmark.txt`; no native terminal screenshot is claimed.

## External limitations

No OpenAI credential is configured, so no paid request or remote model compatibility test
was performed. Provider behavior is verified through real local HTTP and deterministic test
providers. GitLab configuration and local equivalent commands are provided; no hosted
GitLab pipeline was run. Structural remediation checks are not semantic patch-safety proof.
