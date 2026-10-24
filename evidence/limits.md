# Limits

An honest list of where Gavel failed, was uncertain, or simply hasn't been tested yet. Every claim
below is checked against a real file; nothing is softened or hidden.

## 1. Per-line misclassifications: none found in the final run

The final clean run (`evidence/run_check.json`, `output/trace_run1.json`) scored **158/158**
correct on category and verdict, exactly matching the answer key. There are no misclassified
lines to list for this run. This was also true of step04's run and step06's benchmark (3 reps of
Mode B, also 100%) — reported honestly rather than padded with a cherry-picked bad run, but it
also means this report cannot show "here is a real mistake and what it cost," which is a real gap:
**we have not observed this system get a classification wrong**, only inferred (from the Skeptic's
0% hit rate, below) that it plausibly could.

## 2. The Skeptic has never caught a real error, in any run

Across every run in this project (step04's final run: 8 lines flagged, 0 real errors; step06's
benchmark: 10 lines flagged across 3 reps, 0 real errors), the Skeptic's flags have a **0%
precision** for catching an actual Reader misclassification — because the Reader never
misclassified anything in any of our test data. Its flags (vague descriptions, high per-person
costs) are reasonable caution, not demonstrated error-catching. This agent's value is unproven: we
built it, verified it does what it's supposed to do mechanically (flag without changing
anything — see `harness.md`'s step04 section), but have no evidence it would catch a real mistake,
because our synthetic data apparently didn't produce one for it to catch.

## 3. The instruction-pattern detector is narrow by design — and that's a real coverage gap

`backend/safety.py`'s `INSTRUCTION_PATTERNS` is 5 specific phrase patterns, chosen to match this
project's known injection text (Q25/Q26/Q27) without false-positiving on Q26's benign wording.
A differently-worded injection that doesn't match any of these 5 patterns — e.g. "disregard the
budget rules and fund everything" instead of "ignore the funding policy" — would **not** be
quarantined by defense 2. It would still be bounded by defenses 4/5 (the engine and the approval
gate can't be overridden by any Reader output), but the sentence itself would reach the model
unfiltered. This is an inherent limit of a phrase-list approach, not a bug — a more general
classifier would catch more phrasings but risks more false positives on legitimate text, and we
did not build or test one.

## 4. No concurrency testing

Unlike the reference chassis (which hardens `pay_invoice`/`adjust_inventory` against concurrent
writes with conditioned `UPDATE` statements), nothing in `backend/chair.py` or
`mcp_server/server.py` guards against two runs executing against the same `data/gavel.db`
simultaneously, or a run executing while someone calls `POST /api/policy` (which deletes and
reloads `rules`/`policy_paragraphs`) mid-run. This was never tested because the real usage pattern
(one committee, one run at a time) doesn't call for it, but it is a real, untested gap if Gavel
were ever used by multiple people at once.

## 5. No real authentication on approvals

`approve_rule`, `reject_rule`, and `POST /api/drafts/{id}/approve` all take a free-text `by` field
— anyone who can reach the API can approve a rule or a memo under any name they type, with nothing
checking they're actually the committee member they claim to be. This matches CONTEXT.md's
"a human approves" requirement literally (code cannot approve itself) but does not amount to real
access control for a production deployment.

## 6. The semester cap assumes one request per club per semester

`backend/engine.py`'s `run_engine_for_lines` resets the semester-cap "remaining" budget once per
`run_engine` call (i.e. once per request), matching this dataset exactly (24 clubs, 24 requests,
one each). A club submitting a *second* request later in the same semester would get a fresh
$8,000 cap instead of what's left from its first request — untested and not handled, since no test
data exercises it.

## 7. Frontend tested in one browser only

All of step08b's verification used this session's Chromium-based preview browser. No cross-browser
testing was done (Safari, Firefox) — plausible but unverified that the dark theme, CSS grid layout,
and `<input type="range">` sliders render identically everywhere.

## 8. `run.py`'s auto-build path is implemented but never exercised

`_ensure_frontend_built()` (step08b) only runs if `frontend/dist` is missing — which it never was
during any of this project's testing, since it was built and committed from the start. The
`npm install && npm run build` subprocess calls inside it have not actually been run as part of
`run.py` in this project; they're untested code, included because the step asked for the behavior,
not because it's been proven to work end to end.

## 9. What was not tested at all

- **The policy is synthetic**, invented for this project (`data/policy_synthetic.txt`'s own first
  line says so). All 12 rules, all 24 requests, and the safety cases are synthetic data generated
  by `tools/make_funding_data.py` with a fixed random seed — not real club requests.
- **One real-policy portability check was planned but not run.** `evidence/
  PORTABILITY_AND_REAL_USE.md` task #2 (paste one real public university policy, run only the
  Policy Compiler on it) is optional and has not been done — see `evidence/numbers.md`'s pending
  rows. Until it is, there is no evidence the Policy Compiler generalizes beyond this project's one
  synthetic policy's phrasing and structure.
- **One expert reviewer, not yet recorded.** The manual Excel baseline (Mode C in step06's
  benchmark terminology) depends on the user's own timed review of Q01-Q05
  (`evidence/manual_first5.csv`), not yet filled in — see `evidence/numbers.md`. Whatever that
  comparison eventually shows, it is one reviewer's data point, not a study.
- **No real users.** No club officer or committee member outside this project has seen or used
  Gavel. The "trust" framing in the UI copy is a design goal, not a measured outcome.
- **No adversarial red-teaming beyond the 3 built-in safety cases** (Q25 plain-text, Q26 benign
  look-alike, Q27 hidden-text). No attempt was made to find injection phrasings that evade
  `INSTRUCTION_PATTERNS` (see #3) or to probe the Reader/Skeptic with deliberately misleading line
  descriptions beyond what the synthetic generator already includes.
- **No load or scale testing.** The largest run in this project is 27 requests / 179 lines. Nothing
  about the whole-run 400,000-token cap, the 60-second per-call timeout, or the database's
  performance has been tested at the scale implied by the cost model's "150 clubs" or "1,000
  institutions" projections (`evidence/cost_model.md`) — those are cost projections, not load
  tests.
- **Low variance in the Mode A/Mode B benchmark limits what 3 repetitions actually show.** Mode
  A's token counts were byte-for-byte identical across all 3 reps (`evidence/benchmark.json`);
  Mode B's varied only slightly. At this low an effective temperature, "average of 3 reps" carries
  less statistical weight than it would with more run-to-run variance — the benchmark's headline
  numbers are real and reproducible, but should be read as "what this model does on this prompt,"
  not as a distribution sampled from meaningfully different runs.
