# Editorial evaluation workbench

This replaces the dashboard information architecture, not just its theme.

Research consulted [Primer](https://primer.style/), [Carbon data tables](https://carbondesignsystem.com/components/data-table/usage/), [Atlassian empty states](https://atlassian.design/components/empty-state/), [Observable Framework](https://observablehq.github.io/framework/), [GitHub workflow logs](https://docs.github.com/en/actions/how-tos/monitor-workflows/use-workflow-run-logs), and [pytest-html](https://pytest-html.readthedocs.io/en/latest/user_guide.html).

Adopted patterns: Primer's task-oriented navigation and inspection hierarchy; Carbon's
filter/search discipline and expandable detail; Atlassian's actionable empty states;
Observable's readable document structure; GitHub Actions' run-to-job-to-log progression;
test reports' explicit result categories and reproducible exports. Branding and component
code are original. Available skills were inspected; no dedicated frontend-design skill
is installed. Browser tools support actual visual inspection and screenshots.

The user's first questions are what to test, how to start, and what happened. Runs is
therefore a structured, searchable execution list, not a chart or KPI landing page.
Four primary destinations: Runs, Benchmarks, Compare, Documentation. Preferences is
a compact utility. New run is a guided benchmark → agent → permission review → execution
flow. Offline demo is the default; unavailable paid credentials never block it.

Run detail presents outcome in plain language, then findings, observed agent actions,
evaluation evidence, timing/usage, reproduction and exports. Raw JSON and ground truth
are progressively disclosed after execution. Comparison aligns two runs on scenario
and repetition, with explicit missing-result and incompatible-suite warnings.

Warm canvas #F7F6F2; white surface; ink #222321; muted #686A65; hairline #DEDCD5;
dark-red accent #8C3B32. Flat surfaces, small corner radius, no shadows, no sidebar,
no decorative charts, no navigation emoji. Source Sans (Streamlit bundled, SIL OFL)
and a restrained monospace stack support readable prose and evidence identifiers.

Streamlit is retained: native radio navigation, labeled forms, buttons, tabs, expanders,
downloads and responsive structured rows deliver the required journeys without a JS
bundle or new backend API. Presentation modules remain separate from the engine/database.
This is a local single-user utility, not a hosted multi-tenant service.

Verification: real offline launch, run lookup, budget-failure diagnosis, permitted and
denied tool inspection, compatible-run comparison/export, empty/corrupt history states;
AppTest plus browser checks at 1440, 1024 and 390 pixels. No simulated application images.
