# Workbench design system

Use native Streamlit controls; keep presentation separate from execution and storage.
The reference implementation is `src/devsec_bench/dashboard/theme.py` and `.streamlit/config.toml`.

## Color

| Token | Value | Purpose |
|---|---|---|
| Canvas | `#F7F6F2` | Warm page background |
| Surface | `#FFFFFF` | Clear foreground surface |
| Secondary | `#F0EFEA` | Native inputs and quiet supporting surfaces |
| Ink | `#222321` | Main text |
| Muted | `#686A65` | Supporting text, at full opacity |
| Hairline | `#DEDCD5` | Decorative separators |
| Control border | `#85877F` | Distinguishable interactive boundaries |
| Accent / failure | `#8C3B32` | Primary action, focus, genuine failure text |
| Pass | `#37654D` | Passed checks |
| Interrupted / budget | `#7B5A20` | Genuine execution limits |

Text/status tokens meet 4.5:1 on canvas and white; control boundaries meet 3:1.
Tests verify token contrast. Browser QA also checks computed caption opacity and real
native input wrappers: token tests alone cannot establish rendered accessibility.
Always include a semantic status word; color never carries the result alone.

## Type and space

Streamlit's bundled Source Sans interface font is open source under the
[SIL Open Font License](https://github.com/adobe-fonts/source-sans/blob/release/LICENSE.md).
Use the bundled font without a third-party runtime font request. Identifiers, paths,
CLI recipes and JSON use the native monospace stack / Source Code Pro.

Headings: 32px primary (26.4px on mobile), 23.2px section, 17.6px subsection.
Body/control text follows native readable defaults. Avoid more decorative variants.
Use a 4/8/12/16/24/32px spacing scale; separators have 12px vertical margins.
Content width is capped at 1180px with 32px horizontal padding, 16px below 640px.

## Primitives and interaction

- Flat structured rows separated by hairlines; no card wrapper around every item.
- Native labeled text fields, comboboxes, radios, buttons and download controls.
- Corners around 2px; no shadows. Primary action uses restrained red.
- Focus-visible uses a 2px accent outline with 3px offset; native focus states remain.
- Buttons target at least 40px desktop and 44px mobile height.
- Horizontal task navigation wraps on small screens. Columns stack into readable rows;
  comparison preserves Run A/Run B headings. Large optional raw metric tables may scroll.
- Empty states explain the next action. Errors explain what failed and preserve stored data.
- Raw JSON, advanced configuration, optional plots and reference metadata use disclosure.
- Loading execution uses native progress feedback; record real results, never decorative placeholders.

Runs is a list, evaluation is a staged form, findings are a readable document,
actions are chronological expandable rows, and comparison is aligned evidence.
Do not make those screens identical. Preserve URL context when linking to evidence.

## Maintenance check

Review first-run, Runs, wizard, details, findings, actions, Compare, and error states
in the actual app at 1440, 1024 and 390px. Verify native wrapper selectors after
Streamlit upgrades; its DOM may change. Check keyboard focus, labels, overflow,
semantic status words and contrast. Prefer removing an override to growing a custom library.
