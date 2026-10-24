# Screenshots

`report_assets/` already has one full real pass through every screen, captured by the coder
during step08b against a real run (`run-a71a3b35`, 27 requests including the three safety cases,
completed status, real token/cost numbers). Use these directly in the report, or replace any of
them with your own if you want a cleaner run (e.g. without the safety cases, or at a wider
viewport) — just keep the same filenames so report.html's references don't break.

| File | Screen |
| --- | --- |
| `01_start.jpg` | Start — hero, "Try the sample", paste/upload cards |
| `02_rules_proposed.jpg` | Rules — compiled, decoys shown as "not a rule", cards awaiting approval |
| `03_rules_approved.jpg` | Rules — after "Approve all verified" |
| `04_run_in_progress.jpg` | Run — agent nameplates live, progress bar |
| `05_run_completed_injection_banner.jpg` | Run — completed, **the injection-blocked banner** (Q25/Q27) |
| `06_run_event_trace.jpg` | Run — the event feed (glass box trace) |
| `07_review_table.jpg` | Review — verdict chips, filters, the injection banner still visible |
| `08_review_side_panel_citation.jpg` | Review — side panel with the exact policy quote highlighted |
| `09_scenarios.jpg` | Scenarios — pot/alpha sliders, bar chart |
| `10_scenarios_gains_losses.jpg` | Scenarios — who gains/loses between two settings |
| `11_consistency.jpg` | Consistency — inconsistency rate and the disagreeing decisions |
| `12_drafts_approved.jpg` | Drafts — DRAFT labels, an approved memo, Download CSV |
| `13_cost.jpg` | Cost — tokens and dollars from `/api/usage` |
| `14_mobile_responsive.jpg` | Start screen at mobile width, degrading sensibly |

## If you want to re-take any of these

1. `python run.py` from the repo root.
2. Open the URL it prints.
3. Click "Try the sample", approve rules, start a run, then walk through each tab.
4. Screenshot each screen; save over the matching filename above.

## For the real-use/portability evidence (not this file)

See `evidence/PORTABILITY_AND_REAL_USE.md` for the timed-review and real-policy-portability tasks
— those are separate from screenshotting the app.
