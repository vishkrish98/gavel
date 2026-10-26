# Screenshots to take for the report

`report_assets/` already has one full real pass through every screen below (captured by the coder
in step08b, against a real run — `run-a71a3b35`, 27 requests including the 3 safety cases,
completed, real token/cost numbers). Use these directly, or re-take any of them if you want a
cleaner run (e.g. the 24 real requests only, no safety cases) — just keep the filenames so
report.html's references don't break.

For each item below: the screen to open, and exactly what must be visible in the shot.

| # | Filename | Screen / how to get there | What must be visible |
| --- | --- | --- | --- |
| 1 | `01_start.jpg` | Start | The "Try the sample" button, and both the paste-policy and paste-request cards with their hints |
| 2 | `02_rules_proposed.jpg` | Rules, right after compiling | All 12 proposed rule cards (quote + Verified badge) AND at least one decoy card labeled "Not a rule" with its reason |
| 3 | `03_rules_approved.jpg` | Rules, after "Approve all verified" | At least one rule card showing the green "Approved" badge and "approved by ..." |
| 4 | `04_run_in_progress.jpg` | Run, while a run is executing | The 7 agent nameplates with at least one showing "Working…", and the progress bar partway filled |
| 5 | `05_run_completed_injection_banner.jpg` | Run, after a run that includes Q25 and/or Q27 completes | **The injection-blocked banner**, showing the request id, field, and the actual blocked text, plus the run's "completed" status line |
| 6 | `06_run_event_trace.jpg` | Run, scrolled to the event feed | Several real event rows (`agent_run`, `blocked_injection`, `run_end`) with real token/cost numbers visible in at least one row |
| 7 | `07_review_table.jpg` | Review | The verdict-chip column showing at least 3 of the 4 verdict colors (allowed/reduced/denied/needs_docs) in the same screenshot |
| 8 | `08_review_side_panel_citation.jpg` | Review, click a `needs_docs` or `reduced` line | The side panel open, with the exact policy quote highlighted in the "Rule citation" block |
| 9 | `09_scenarios_two_settings.jpg` | Scenarios | Scenario A and Scenario B side by side at two different alpha values (e.g. 0 and 1), with visibly different bar charts — this is the "sliders at two settings" requirement, satisfied in one shot since the screen already shows both scenarios at once |
| 10 | `10_scenarios_gains_losses.jpg` | Scenarios, scrolled down | The "Who gains and loses, A → B" table with real club names and dollar changes |
| 11 | `11_consistency.jpg` | Consistency | The inconsistency rate stat and at least one row of the "Decisions that disagree with the policy" table |
| 12 | `12_drafts_approved.jpg` | Drafts | The decision memo with a green "Approved" label, plus at least one per-request question draft still marked DRAFT |
| 13 | `13_cost.jpg` | Cost | The total cost figure and the input/cached/output token breakdown, both real numbers from `/api/usage` |
| 14 | `14_mobile_responsive.jpg` | Start, at mobile width (375px) | The layout degrading to one column, nav wrapping, nothing cut off |
| 15 | `15_safety_pass_table.png` | Terminal, after `python -m safety_test` | **The full PASS/FAIL table** (all 13 checks) and the "Overall: ALL PASS" line — this is a terminal screenshot, not a browser one |
| 16 | `16_clubs_registry.jpg` | Clubs tab, after a run | Several clubs' pre-approved budget, spent, and remaining balance columns, with real (non-zero) numbers — added post-11b for the club/budget bulk-import feature |

## How to (re-)take any of these

1. `python run.py` from the repo root; open the URL it prints.
2. Click "Try the sample", approve rules, start a run (include Q25/Q26/Q27 if you want #5 to show
   a real blocked injection — they're loaded automatically by "Try the sample").
3. Walk through each tab; screenshot each screen as listed above.
4. For #15, run `python -m safety_test` in a terminal and screenshot its printed table directly
   (no browser involved).

Save every file into `report_assets/` with the filename shown above.

## Not screenshots — separate evidence

- `evidence/manual_first5.csv` / running `python -m score_manual` — your timed Excel baseline,
  not a screenshot task. See `evidence/PORTABILITY_AND_REAL_USE.md`.
- `evidence/numbers.md` — the master index of every number the report cites, with its source file.
- `evidence/limits.md` — the honest list of where the system failed or wasn't tested.
