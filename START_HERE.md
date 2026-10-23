# Gavel kit: start here

Everything for the MGT 409 final project is in this folder. Gavel is decision support for a student-government funding committee: policy turned into approved, quote-verified rules; every budget line checked by code with a citation; consistency checks; funding scenarios. Hard deadline: Mon Oct 26, 6:00 PM on Canvas. Target: submit Sunday night, keep Monday morning as buffer.

## 15-minute setup (do once)

1. Make a parent folder (for example `mgt409`). Unzip this kit inside it and rename the folder to `gavel`. You should have `mgt409/gavel/CONTEXT.md`.
2. Put your real key in `mgt409/.env` (the PARENT folder, one level above the repo), one line: `PORTKEY_API_KEY=your-course-key`. Never put the key inside `gavel/`.
3. Python 3.11+ and Node 20+ (same as HW5). Create an empty GitHub repo named `gavel` (public, or add `zlisto` as collaborator).
4. Open Claude Code inside the `gavel` folder.
5. Sanity check (30 seconds): `python3 -I tools/make_funding_data.py /tmp` should print `requests 24 lines 158 {'allowed': 95, ...}` (it writes into /tmp; do not run it into data/).

## How to drive your coder

For each step, paste exactly one line, changing the file name:

    Read CONTEXT.md, then do everything in PROMPTS/step00_skeleton.md. Stop when it says stop.

Steps in order: step00_skeleton, step01_data_layer, step02_mcp_tools, step03_engine, step04_agents, step05_token_logging, step06_benchmark, step07_safety, step08a_backend_routes, step08b_frontend, step08c_portability (stretch), step09_readme_fresh_clone, step10_evidence_pack, step11a_report, step11b_slides.

After each step: read what it reports, check the "done when" below, `git commit`, and add a note to `AI_prompts.md`. Keep the PROMPTS folder in the repo; it is your prompt log.

Done-when checks:
- 00: `python run.py` starts with `.env` in the parent folder AND in the repo folder.
- 01: loader prints 16 policy paragraphs, 24 requests, 158 lines, 30 prior decisions, 2 hidden-text flags.
- 02: `tests/test_mcp.py` passes; `output/mcp_smoke.json` shows a verified quote and a fake quote rejected.
- 03: `evidence/engine_eval.json` shows 158/158 verdicts and amounts match, optimizer matches the key to the cent, 6/30 inconsistent decisions found, zero tokens.
- 04: pipeline runs end to end and prints accuracy against the keys; decoy paragraphs turned into rules = 0; `output/trace_run1.json` exists.
- 05: real usage table; `evidence/cost_model.md` has 24-club, 150-club and 1,000-institution rows.
- 06: `evidence/benchmark.md` has Mode A vs Mode B plus five experiments.
- 07: `evidence/safety_results.json` shows before/after, Q26 NOT quarantined, zero false positives. Screenshot the PASS table.
- 08a/08b: click "Try the sample", approve rules, run, open a line and see the highlighted policy quote, move the scenario sliders and watch the chart update.
- 09: `evidence/fresh_clone_log.md` shows clone to first result well under 10 minutes; secrets check clean.
- 10: `evidence/numbers.md` exists and every number points to a file.
- 11: `report.html` (10 to 15 printed pages) and `slides.html` (10 slides) open by double-click with no `[[USER` or `[[MISSING` left.

## Schedule (you said you can work as long as needed; this is the safe order)

- Fri night: setup, the stopwatch baseline (below), steps 00 to 03.
- Sat morning: steps 04, 05. Afternoon: steps 06, 07. Evening: step 08a.
- Sun morning: step 08b (the UI is the biggest step). Afternoon: 08c if on schedule, then 09 and 10, screenshots. Evening: fill placeholders, steps 11a and 11b, push, final checklist, submit.
- Mon morning: buffer only. Fix, re-run the fresh-clone test, submit before noon.

## Your tasks (the coder cannot do these)

1. STOPWATCH BASELINE, tonight, BEFORE step 04 (about 40 min). Open `evidence/manual_first5_requests.txt` and `data/policy_synthetic.txt`. Review the five requests (Q01 to Q05) the way you would in Excel, with a stopwatch, and fill `evidence/manual_first5_TEMPLATE.csv` (save as `evidence/manual_first5.csv`). Do NOT open the answer key or any app output. Write down your minutes.
2. SCREENSHOTS after step 08b, using `evidence/SCREENSHOTS.md`. Save in `report_assets/`.
3. MOTIVATION PARAGRAPH, in your own words (6 to 8 sentences): how funding review works in a student government, where inconsistency creeps in, what it costs clubs and the committee. Draw on your RPI Union experience; only numbers you can stand behind, labeled as estimates when they are. No real names.
4. COMPETITOR CHECK: open the sites of at least two real products (for example CampusGroups and Campus Labs) and write one line each on what they say they do, with the link. Do not claim features you did not read.
5. REAL-USE EVIDENCE: follow `evidence/PORTABILITY_AND_REAL_USE.md` (your timed Excel review, the optional real-policy portability check, your reflection).
6. Commit after every step. Never paste your key into a chat, prompt or file in the repo.

## Final checklist

Repo
- [ ] Link opens in a private browser window (or `zlisto` added as collaborator)
- [ ] README.md and .env.example at the root; .env.example has names only
- [ ] `git ls-files` shows no secrets, database files or anything from data/private/
- [ ] Fresh clone in a new folder runs with .env one folder up, in under 10 minutes
- [ ] frontend/dist committed; data files, AI_prompts.md, PROMPTS/, harness.md in the repo
- [ ] Only gpt-6-luna appears in the code
Report and slides
- [ ] report.html opens by double-click with wifi off; 10 to 15 pages in Print Preview; all 8 sections
- [ ] Search both HTML files for `[[USER` and `[[MISSING`: none left
- [ ] Every number matches evidence/numbers.md
- [ ] slides.html opens by double-click; 10 slides or fewer; readable
- [ ] The report says plainly that policy and requests are synthetic and the human baseline is one expert on five requests
- [ ] No real club, student or university policy text anywhere in the repo
Canvas
- [ ] Submit exactly what the Canvas page asks (repo link, report.html, slides.html, video if any). Screenshot the confirmation.

## If you run short of time

Cut in this order: demo video; step 08c portability; the consistency screen polish; the sequential-vs-parallel and cache experiments; HTML upload.
Never cut: per-call token logging and cost model; the safety test with before/after, the Q26 false-positive control and a screenshot; the Mode A vs Mode B head-to-head; one traced real run; your Excel baseline; the fresh-clone test.
If the coder is stuck over 45 minutes: tell it to build the simplest version that meets the done-when line and move on.
If accuracy is low: report it honestly. You may change prompts at most twice; write each change down and say in the report that prompts were tuned on the same test data.
If the injection does not fool the model with defenses off: report that as it is; show the pre-model layers still caught it.
If the course key hits a limit: run the benchmark once per mode and say so.

## What is in this kit

- CONTEXT.md: the brief your coder reads every time.
- PROMPTS/: one prompt file per step (15).
- data/: synthetic policy (16 paragraphs, 12 rules), 24 requests with 158 lines, answer keys, club history, prior decisions, safety requests. Do not edit.
- tools/: the generator and reference rule engine.
- evidence/: manual baseline sheets, real-use and portability plan.
- .gitignore, .env.example, AI_prompts.md: ready to use.
