# Professional dashboard redesign

The user's UI task governs this bounded redesign of the existing Streamlit app.
Preserve evaluator, provider, registry and storage behavior. Dark tokens use #0B0F17
background, #111827 navigation, #161E2D cards, #2A3546 borders, #F1F5F9 text and
#94A3B8 secondary text. Blue is the primary action, green success, amber incomplete
or budget-limited work, and red execution/safety failures. Status always has a text label.

Navigation: Overview, Benchmark Runs, Scenarios, Agent Comparison, Execution Traces,
Reports, Settings. A page title and description sit beside an offline Run Benchmark
action. All page routes are bookmarkable; old Benchmark Results routes map to Runs.

Presentation modules derive overview measures, scenario/model rollups, status rows,
and dark Plotly layouts from existing Run objects. No business/evaluation code changes.
The dashboard caches history with the database modification time as its invalidation
key; launching an offline benchmark clears the cache. Settings remain in session state.

Overview: five truthful metrics, time trend, scenario bars, model outcomes and recent
runs. Benchmark Runs: real scenario results with filterable/sortable tables and detailed
inspection. Scenarios: task, tools, limits and repository scope; reference answers remain
inside an explicitly labeled evaluator-only expander. Comparison: selected-run cards,
success/failure distribution, latency, known cost and token history. Traces: chronological
permission/output-size events with expandable JSON, final findings and evaluation;
raw provider reasoning/tool response bodies are explicitly unavailable, never invented.
Reports: sanitized downloads and report preview. Settings: bounded offline defaults,
history location, security boundaries and CLI guidance for paid models.

Use native Streamlit containers, metrics, forms, tabs, tables and expanders. CSS only
styles shared cards, typography, navigation and narrow-screen metric wrapping. Avoid
DOM manipulation or custom frontend orchestration. No remote fonts/telemetry assets.

Verification: test derived measures against known stored outcomes; AppTest all seven
views, empty/incomplete states, filters and run launch; lint/types/full tests; visual browser
inspection of desktop/laptop/tablet widths; recapture real screenshots and publish.
