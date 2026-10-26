# AI Prompts Log — Gavel

Log of prompts typed into the vibe coder (Claude Code) while building this project. One section per step. PROMPTS/ holds the full text of every step file referenced below.

## Step 00: Skeleton

- "Read CONTEXT.md, then do everything in PROMPTS/step00_skeleton.md. Stop when it says stop."

No follow-up needed — the instructions were complete on the first prompt. Cloned vishkrish98/hw5 as a reference chassis (outside the repo, not committed) and created backend/, mcp_server/, frontend/, output/, tests/, with requirements.txt pinned to the versions that reference project uses. Built a root-level env_loader.py (checks the repo folder's .env, then the parent folder's, with a friendly error naming both if PORTKEY_API_KEY is missing) and run.py (picks a free port from 8000, starts the backend, prints the URL). Proved run.py works with .env in the parent only, then the repo only, then moved it back to the parent. Venv created, dependencies installed clean.

## Step 01: Data layer

- "Read CONTEXT.md, then do everything in PROMPTS/step01_data_layer.md. Stop when it says stop."

No follow-up needed. Built backend/db.py (the SQLite schema) and backend/load.py (`python -m backend.load`). backend/hidden_html.py parses the Q27 safety-test HTML the way a naive scraper would, flagging font-size:0 and white-on-white elements separately. Loader output matched every expected count exactly: 16 policy paragraphs, 27 requests, 179 lines, 30 prior decisions, 2 hidden-text flags. Deliberately left several fields unloaded because they belong to later steps: policy kind (step04's job), line category/headcount/qty/nights (the Reader's job), and the answer-key fields on prior decisions.

## Step 02: MCP tools

- "Read CONTEXT.md, then do everything in PROMPTS/step02_mcp_tools.md. Stop when it says stop."

No follow-up needed on the instructions, but building this step surfaced two real bugs, found by actually running the 18 tests rather than just reading the code: (1) `db.init_db` couldn't `DROP TABLE` under foreign-key enforcement and hit `sqlite_sequence` — fixed by disabling the FK pragma during the wipe and skipping `sqlite_*` tables. (2) `consistency_report`'s first matching key (description + amount + docs) had 36 real collisions across different clubs in the actual data — switched to (club, description, amount, docs), which is unique. Built mcp_server/server.py (FastMCP stdio, all 12 deterministic tools), backend/engine.py, backend/pricing.py, backend/quotes.py, backend/audit.py. tests/test_mcp.py (18/18 passing) proposed and approved the 12 true rules through the real tools, got a 158/158 engine match and a 6/30 consistency match against the answer key. `output/mcp_smoke.json` records a verified quote, a rejected fake quote, and every other tool's real result, with an honest note that the calls were made in-process rather than over stdio.

## Step 03: Engine validation

- "Read CONTEXT.md, then do everything in PROMPTS/step03_engine.md. Stop when it says stop."

No follow-up needed. Added tools/make_engine_eval.py, which proposes and approves the 12 true rules through the real tools, writes the true line facts as a labeled test fixture (standing in for the step04 Reader, which doesn't exist yet), then validates `run_engine`, `allocate`, and `consistency_report` against the answer key. Result: 158/158 lines match verdict and amount exactly, `allocate` matches the optimizer answer key to the cent across all 4 scenarios, consistency finds 6/30 inconsistent. Zero model calls, confirmed in `evidence/engine_eval.json`. No code changes were needed anywhere — step02's implementation already reproduced the answer key exactly.

## Step 04: Agent team

- "Read CONTEXT.md, then do everything in PROMPTS/step04_agents.md. Stop when it says stop."

No follow-up needed — the first step with real model calls. Built backend/models.py, backend/prompts/*.md (one file per agent, each explicitly told that line/justification/policy text is data, never instructions), backend/agents.py (shared gpt-6-luna/Portkey config, reasoning_effort=low), backend/chair.py (CHAIR is plain Python orchestration, not an LLM agent), and backend/run_check.py. Real, untuned run1 results: 100% rule recall/precision, 0 decoys turned into rules, 100% category and verdict accuracy, 158/158 lines exact on both verdict and dollar amount, 30/30 consistency agreement with step03's baseline, 10 Skeptic flags (0 were real misclassifications). 61 model calls, 103,793 tokens, $0.016. Spot-checked two euphemism cases by hand (gift cards, cocktails) to make sure the near-perfect score wasn't a data leak — both correct. Nothing was tuned for accuracy, per the step's own instruction.

## Step 05: Token logging and cost model

- "Read CONTEXT.md, then do everything in PROMPTS/step05_token_logging.md. Stop when it says stop."

No follow-up needed. Verified `log_usage` (built in step02) already logs the provider's real response fields with no estimation, by printing one raw usage object and confirming the exact field names match what chair.py passes through. Dated backend/pricing.py against the course's own pricing table. Added `GET /api/usage` and `GET /api/runs`. Built backend/projection.py (one labeled assumptions block, everything else derived from measured data) → evidence/cost_model.md: $0.000751 to compile the policy once, $0.000632/request, $0.000096/line, $0.016 for the 24-club semester (measured), $0.096 for 150 clubs and $16.04 for a 1,000-institution platform (both labeled assumptions), $6.67/request for a human reviewer vs. $0.00063/request for Gavel's first-pass packet.

## Step 06: Mode A vs. Mode B benchmark

- "Read CONTEXT.md, then do everything in PROMPTS/step06_benchmark.md. Stop when it says stop."

No follow-up needed on the instructions, but one real bug was found and fixed while building it: `reload_fresh_db()` between Mode B repetitions was wiping the usage table each time, so two of the five experiments were reading from a run_id whose data no longer existed — fixed to reference the last completed repetition instead. Built backend/benchmark.py: Mode A (one generic prompt, no tools) vs. Mode B (Compiler + Reader + Skeptic + the code Engine, no Drafter/consistency/optimizer, per the step's own literal definition), each run 3 times fresh, plus 5 experiments on Mode B. First-pass numbers (later found to be miscounted — see the October 26 entry below) showed Mode B ahead on dollar accuracy and citations, reported honestly alongside where Mode A did almost as well. Mode C (human baseline) reported as genuinely not-yet-available, since it depends on the user's own timed exercise.

## Step 07: Safety and prompt-injection defenses

- "Read CONTEXT.md, then do everything in PROMPTS/step07_safety.md. Stop when it says stop."

No follow-up needed on the instructions. Building and testing it surfaced the same class of bug as step06 (`reload_fresh_db()` wiping the audit table before the final excerpt could be built) — fixed by capturing each case's excerpt immediately after it finishes, rather than at the end of the whole run. Also found a real, pre-existing data-format quirk unrelated to injection defenses: `data/requests_truth.json`'s Q27 entries assume document attachments the HTML rendering never actually wrote into the markup, so comparing Q27 directly against that file produced false mismatches — added a fair-baseline recomputation specifically for Q27. Built backend/safety.py (hidden-text stripping, instruction-pattern quarantine, delimiter wrapping, one `DEFENSES_ENABLED` toggle). `safety_test.py`: 13/13 checks PASS, including the Q26 false-positive control (0 wrong quarantines) and a 5,000-token cap run ending cleanly. Reported honestly that the model actually resisted the injection on its own even with defenses off in this run, rather than claiming the defenses caught something they never faced.

## Step 08a: Backend routes

- "Read CONTEXT.md, then do everything in PROMPTS/step08a_backend_routes.md. Stop when it says stop."

No follow-up needed on the instructions, but testing the real app surfaced two real bugs: (1) `POST /api/runs` needed to be `async def`, not `def` — a sync route has no running event loop for `asyncio.create_task` to use. (2) Generalizing `backend/hidden_html.py` beyond its one Q27 fixture surfaced a `<title>`-tag text leak into justification text, fixed by skipping `<title>` content (re-verified Q27's own parse stayed byte-for-byte unchanged). Built the full FastAPI route surface: policy upload/compile/approve/reject, request upload (JSON paste, txt/html/json file upload), the zero-upload demo, the run lifecycle, consistency, the optimizer, line explanations. `tests/test_api.py`: 27/27 passing against the real app and a real database, including real model calls.

## Step 08b: Frontend

- "Read CONTEXT.md, then do everything in PROMPTS/step08b_frontend.md. Stop when it says stop."

No follow-up needed on the instructions. One real bug found while testing: an early test click used an ambiguous CSS-class selector that matched multiple buttons across different screens and landed on the wrong one — fixed by adding explicit ids to every primary action button (not a product bug, a test-selector problem). Built the React/Vite/TypeScript frontend, dark/scholarly/brass theme, all 9 screens against the real backend with real model calls — verified end to end in the browser: demo load, compile, approve all verified, a 27-request run including the 3 safety cases, the injection-blocked banner firing for real on Q25 and Q27, reviewing verdicts with a real policy citation in the side panel, the scenario sliders, consistency, approving a draft, and the cost screen. Zero console errors throughout; tested at 375px mobile width. Built and committed frontend/dist; fixed Vite's own `.gitignore` (it excluded `dist` by default).

## Step 08c: Portability (deferred)

PROMPTS/step08c_portability.md was explicitly marked as an optional stretch step in START_HERE.md's own time-management guidance. Skipped at the time to move directly to step08b; effectively superseded later (October 26) by a more thorough real-policy portability test — see that entry below.

## Step 09: README and fresh-clone test

- "Read CONTEXT.md, then do everything in PROMPTS/step09_readme_fresh_clone.md. Stop when it says stop."

No follow-up needed. Rewrote README.md in full (prerequisites, install commands for macOS/Linux and Windows, exact `.env` placement, how to run tests/benchmark/safety checks, troubleshooting). Fixed `.env.example` to be strictly names-only. Ran a real timed dry run: a local git clone into a brand-new folder (no GitHub remote existed yet, noted honestly rather than claimed as a network clone), fresh venv, `pip install` (clean, 26.29s), `.env` one folder above, `python run.py`, then a full sample run end to end via direct API calls. 53.0s of active stage time, 112.6s wall-clock total, both well under the 10-minute budget. Security check: `git ls-files` plus the full git history showed no `.env`, no database files, nothing from `data/private/`, and no key-shaped strings anywhere tracked.

## Step 10: Evidence pack

- "Read CONTEXT.md, then do everything in PROMPTS/step10_evidence_pack.md. Stop when it says stop."

No follow-up needed. Ran the final clean pipeline on all 24 requests (identical shape to every prior run). Built evidence/numbers.md, indexing every citable number to its real source file, with 3 rows explicitly marked PENDING for the user's own stopwatch and portability tasks rather than inventing placeholder numbers. Built evidence/limits.md: an honest account that no line in any run of this project has ever come out misclassified (so there was no real mistake to show yet), the Skeptic's 0% observed precision across every run, the injection detector's phrase-list being narrow by design, and a list of untested gaps (concurrency, auth, scale, cross-browser). Wrote score_manual.py, tested against a throwaway perfect-score CSV to confirm the scoring logic before deleting that test file so no fake baseline was left behind.

## Step 11a: Report

- "Read CONTEXT.md, then do everything in PROMPTS/step11a_report.md. Stop when it says stop."

No follow-up needed on the instructions, but two real rendering bugs were caught by visually inspecting the rendered PDF rather than trusting the generator code: raw Python booleans (`True`/`False`) were leaking directly into prose text, and "Sum |allowed-dollar error|"'s pipe characters rendered as what looked like lowercase L's in this font at this size — reworded to avoid the ambiguous glyph. The first draft also came in at 18 printed pages (over the 15-page maximum), verified with headless Chrome plus PyMuPDF's page count since no PDF tool was installed; trimmed body font size, removed forced page breaks between sections, shrank embedded images, and dropped 3 unused images to land at 11. Built tools/make_report.py, which generates report.html programmatically from files in evidence/ and output/ so every number is read from a real file rather than retyped by hand, with a hand-built inline SVG agent diagram and a live-generated SVG token-by-agent bar chart.

## Step 11b: Slides

- "Read CONTEXT.md, then do everything in PROMPTS/step11b_slides.md. Stop when it says stop."

No follow-up needed. Built tools/make_slides.py, generating slides.html as a reveal.js 5.1.0 deck of exactly 10 slides, loaded from the pinned cdnjs CDN per the step's own instruction, with screenshots and the agent-team SVG embedded as base64. Resolved one real ambiguity up front: the step's "load from the CDN" instruction appears to conflict with the project's broader self-contained/offline philosophy for report.html, but `START_HERE.md`'s own final checklist only requires that slides.html "opens by double-click," with no "wifi off" requirement like report.html's — so a live CDN script tag for the framework itself is in bounds, while every image still stays embedded. Verified every one of the 10 slides in a headless-browser screenshot, stepping through the deck one at a time: no overflow, no console errors, speaker notes present on all 10, body text well over the 28px minimum.

## October 26: Real-policy portability check

- "can you look at RPI's policy and clubs, I want to do a simulated run"

Completed evidence/PORTABILITY_AND_REAL_USE.md's optional task #2 (the real-policy portability check) at the user's direct request, effectively standing in for the step08c stretch step that had been skipped earlier. Pasted a real, public university student union's funding policy into `data/private/real_policy.txt` (gitignored, never committed, per the task's own "do not publish the policy text" instruction), reformatted it to Gavel's paragraph format, and ran the real Policy Compiler through the live app's own API, no special code path. Of 22 real paragraphs, only 4 became enforceable rules, all 4 quote-verified, 0 corrected by hand. Then ran a simulated pipeline on 6 fabricated requests against those 4 rules (also gitignored) and found 3 concrete errors: a travel-mileage line mis-categorized as "supplies" and wrongly capped; one real paragraph bundling 5 distinct dollar rules into a single piece of prose, of which the compiler kept only the headline rate, crushing two valid food lines (one to $0); and a cash-prize line allowed in full despite a real prohibition the schema already supports but the compiler never recognized. Also found a structural gap: no rule type exists for percentage-based subsidies at all, and the real policy is built around them. Wrote the full results into evidence/PORTABILITY_AND_REAL_USE.md and report.html's portability section, labeled as a real, not-flattering limitation rather than a success story. Reset the live database back to the synthetic demo state afterward.

## October 26: Canvas submission clarification from course staff

- (Pasted) A message from the TA: Canvas accepts a URL or files, not both, so submit files only (report.html, slides.html, optional video); the GitHub repo link has to live inside those files or graders can't clone the repo; note explicitly if the repo is private.

Fixed a real gap this surfaced: slides.html had no GitHub repo URL anywhere, and neither file mentioned what to do if the repo is private. Added a repo-URL placeholder to slides.html's title slide and expanded both files' placeholder text to prompt for a private-repo note, since this is now the only way the repo link reaches a grader.

## October 26: Manual Excel baseline (Mode C)

The user completed START_HERE.md's stopwatch task directly: reviewed Q01-Q05 (34 lines) against the real policy, no answer key, no app, in 17 minutes, and filled `evidence/manual_first5.csv`.

- "Total minutes: 17"

Ran `python -m score_manual`: 0.882 verdict accuracy, $3,210.00 wrongly allowed, 0.842 rule-citation accuracy. Wired tools/make_report.py to read `evidence/manual_first5_scored.json` directly (falling back to the original placeholders if that file doesn't exist yet) and replaced 3 of report.html's placeholders with the real numbers. Verified the $3,210 figure line by line against the scored JSON before writing analysis prose about it, and corrected a first draft of that paragraph that had conflated two different scorer metrics (the dollar total covers 4 mismatched lines; a separate "wrongly allowed count" field is a stricter 2-line subset) before it went into the committed report.

## October 26: "Could we increase the accuracy of Gavel?"

- "Could we increase the accuracy of gavel?"
- "Like for an AI generated software we should pushing for 95% or above"

Diagnosed before touching any prompt, since changing a prompt this close to the deadline would have required the "tuned on the same test data" disclosure the course rubric asks for. Ran Mode B once in isolation and found zero real verdict mismatches despite a reported 0.883 accuracy — traced this to a real scoring bug in `backend/benchmark.py`'s `load_truth()`, which built its truth key from all 179 lines in `data/requests_truth.json` (including step07's Q25-27 safety cases) instead of the 158 lines `PROMPTS/step06_benchmark.md` actually scopes this comparison to, inflating every accuracy denominator with 21 lines neither mode was ever asked to classify. Confirmed precisely before fixing: Mode A's old reported 0.860 × 179 = 154.0 exactly, meaning its real accuracy on the 158 scored lines was 97.47%, not 86.0%. Fixed the scope in `load_truth()` (a scoring-code fix, not a prompt change). While re-running, found a second issue: experiment 4 (parallel vs. sequential) showed parallel as *slower* — traced to a one-time connection-warmup cost on the first call in a fresh process, not a real parallelism finding, fixed with one untimed warm-up call and verified sane afterward (2.76x). Re-ran the full benchmark for real: true numbers are Mode A 98.1% verdict accuracy and Mode B 100%, both far higher than previously reported, with Gavel's real remaining edges being $0 wrongly allowed (vs. $9,500 for Mode A) and perfect citation and needs_docs handling. Rewrote the Impact section's narrative prose in both file generators rather than letting the numbers silently update — the old framing ("human baseline essentially tied with Gavel, ahead of Mode A") was true under the buggy numbers and became false under the corrected ones, since both AI modes now clearly beat the human baseline.

## October 26: Motivation and real-world reflection paragraphs

- "1. I was on the RPI Union Executive Board... 2. I saw inconsistency during the annual review cycle... 3. A typical review took about an hour... 4. It cost issues where clubs would push back..." (answers to four direct questions about real RPI Union experience)
- "Please make sure that it writes like a human, no em dashes and such."
- "make sure that the em dash rule and others gets applied to everythign else, want to make sure it reads that a human made this"
- (Attached) a real, current PDF of the Rensselaer Union Guidelines and Procedures, with: "feel free to look up what the RPI Exec board did from 2018-2020. also here is the RUGP"
- "I cant [remember a specific decision] since it was over 8 years ago"
- "No thats weird, remember this is the final project for a class"
- "Also take a look at Yale SOM's work and how they do things"

Drew out the real motivation content through direct questions (role history, a specific inconsistency observed, rough time estimates, real cost) rather than inventing it, then revised through two rounds of feedback: removing repeated "(estimate)" parenthetical tags for more natural phrasing, and removing a choppy short-sentence pattern that itself read as an AI tell. Researched the user's current, real Yale SOM Clubs & Finance Committee role (a public handbook page, which also happened to confirm the user's real name as a current C&F chair) to sharpen the paragraph with a specific, currently-relevant, verifiable comparison, since Yale SOM's own tiered dollar/attendee review thresholds still turned out to have real overlapping ambiguity in the written policy. Wrote the real-world reflection honestly around the general remembered pattern (six review rooms, inconsistent food-rule application) instead of fabricating false specificity for a decision the user explicitly couldn't recall in detail after 8 years, then rewrote its register after the user flagged an early draft as "weird" for a graded submission. Followed up by doing a full em-dash and short-choppy-sentence cleanup pass across every piece of generated prose in both tools/make_report.py and tools/make_slides.py, not just the new paragraphs, checking each of roughly 44 instances individually rather than a blind find-and-replace, and deliberately leaving the one em dash that appears inside a verbatim-quoted real Drafter-agent trace output untouched, since changing quoted evidence would misrepresent the real data. Also caught and fixed two stale "next steps" claims left over from tasks that had already been completed earlier in the session. Inserted the already-researched competitor paragraph (CampusGroups, Anthology Engage) into both files in the same pass.

## October 26: Open the app in the browser

- "can you open gavel in the browser?"

Started the app's dev server and confirmed it's reachable both in the sandboxed preview pane and on the user's own machine at `http://localhost:8000/`, no code changes.

## October 26: This log's own format

- "can we update the Ai prompts to look like what we did for Hw5?"

Rewrote this file from the kit's original one-row-per-step table into the narrative, quote-then-prose format used in `Homework/HW-5/AI_prompts.md`, preserving every real technical detail (bug numbers, dollar figures, file names) from the previous version rather than summarizing them away.

## October 26: Club and budget import

- "its still not opening up" (the Gavel server had been stopped by my own earlier preview-tool cleanup; restarted it detached so it survives independent of my tools)
- "can we make a sample like for RPI, you have all the docs for it" (loaded the real RPI policy and 6 simulated requests into the live app so the user could explore it in the browser, same data as the earlier portability check)
- "Also we need to be able to import clubs and budgets and such with all of this"

Asked two clarifying questions before building, given it was deadline day: whether this was for the user's own exploring or a real feature for the graded submission, and what exactly "import clubs and budgets" should cover. The user answered: a real app feature, covering bulk requests, club entities with running budgets, and designed with an eye toward actually rolling out to RPI and Yale SOM.

Added a new `clubs` table (`backend/db.py`) and `backend/clubs.py`, modeled on two real, researched funding patterns rather than an arbitrary number: Yale SOM's C&F grants a flat $1,000 per club at the start of the year (from the earlier handbook research), RPI's Union instead sets a variable per-club amount during annual budgeting (from the real policy already pulled for the portability check). Deliberately joined to `requests.club` by name instead of a foreign key, the same convention the engine's consistency check already uses, so the whole feature stays additive and doesn't touch anything in the already-graded pipeline. Added three routes (`GET /api/clubs`, `POST /api/clubs/bulk`, `POST /api/requests/bulk`), a new Clubs tab in the frontend with two paste-or-upload import panels, and seeded the demo's 24 synthetic clubs from `club_history.json`'s existing `last_year_allocated` field.

Found and fixed one real bug while testing live rather than just reading the code: `list_clubs_with_balances`'s "most recent run touching this club" subquery joined three tables and referenced a bare `rowid`, which SQLite rejected as ambiguous — qualified it to the specific table's rowid. Wrote 8 new tests (`tests/test_clubs.py`) against the real FastAPI app and a real database: demo seeding, bulk-import validation and partial-success reporting, re-import-by-name updating instead of duplicating, and the balance math itself verified against a directly-inserted verdict row (the same labeled-test-fixture pattern step02/03 use to isolate one layer, since a real verdict otherwise needs a full model-driven pipeline run). 53/53 tests passing. Verified visually in the browser against the real RPI data from the earlier portability check: a real club came back over budget (negative balance, rendered in red), confirming the balance math on genuine, non-trivial data rather than just a happy-path number.

## October 26: Sample RPI run, and updating the report/slides for the new feature

- "run a sample run for rpi. but lets also update everything"
- "also what if clubs gave a line by line aleady for tjier budget?"

Explained before building anything further: a club's full line-itemized budget is already exactly what a Gavel "request" is (one club, many lines, each checked independently), so this needed no new feature, just the bulk-import route already built. Reloaded the real RPI policy, bulk-imported the 6 real clubs with budgets, and bulk-imported all 6 requests in a single call (demonstrating the new endpoint rather than one at a time), then ran the real pipeline. Took a screenshot of the Clubs tab for the report, then realized the first one showed real RPI club names — reset to the synthetic demo data and re-ran it specifically to get a screenshot with no real club names in it, consistent with the conservative stance already established for the portability check, before it went into a committed file. Added a new paragraph and figure to report.html's "What is new" section (closing the other half of the competitor-gap argument: CampusGroups/Anthology Engage track budgets but don't check policy, Gavel now does both) and one new table row to the matching slide. Regenerated both, re-verified report.html stayed at 12 pages and slides.html's changed slide had no overflow, 53/53 tests still passing. Reloaded the real RPI demo data back onto the live app afterward so the user could keep exploring it.

## October 26: Optional goal/program hierarchy, so Gavel works with differing club structures

- "we need to add more content to these slides these are not consulting level. Also at RPI during the annual budget process every club writes a goal and under each goal is a program (an event) and then it goes to line items basis."
- (clarifying question asked: richer slide content only, or a real feature?) "We want to be able for gave to work with differing club structures"
- "Like remember that RPI does their budgeting for the entire year over a weekend and then any addiitonal requests they use thier weekly meeting for"

Added two new nullable columns on `lines` (`goal`, `program`) rather than new tables, and deliberately kept them out of `backend/engine.py` entirely: a line's verdict and citation never depend on which goal or program it's filed under, only its own description/amount/docs, so every one of the 158 real answer-key lines has both columns NULL and behaves exactly as before. Flowed through both places a line enters the system (`backend/load.py`, `backend/requests_intake.py`) and back out through two explicit field allowlists that needed the new names added by hand (`mcp_server/server.py`'s `_line_dict`, `backend/main.py`'s verdicts query). Added an automatic "Group by goal / program" toggle to the Review screen that only appears when at least one visible line actually has the data, so a flat club's screen looks exactly like it always has.

Wrote 4 new tests proving the engine produces an identical verdict whether or not a line carries a goal/program tag (calling the real engine directly, bypassing the model). Verified the grouping logic against real API data in the browser console before trusting a screenshot, after the UI's own request-selection checkboxes proved genuinely flaky to drive by script during manual testing — confirmed this was a test-automation problem, not a product bug, by querying the resulting runs' verdicts directly each time. 57/57 tests passing.

When the user added the real detail about RPI's two cadences (annual weekend budgeting vs. weekly additional requests), updated both the Start and Clubs screens' copy to say explicitly which flow matches which cadence, rather than adding a new "submission type" field purely to label a distinction the two existing import paths (bulk vs. single) already represent structurally.
