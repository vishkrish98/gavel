# Gavel

Gavel is decision support for a student-government funding committee: it turns a funding policy
into machine-checkable rules you approve, then checks every club's budget line against them with
a citation and a dollar amount. It recommends and explains — your committee always decides.

See [`harness.md`](harness.md) for the full technical write-up (data tables, MCP tools, the
engine, agents, API routes, safety rules).

## Prerequisites

- **Python 3.11 or newer.**
- **Node is NOT needed.** The built frontend (`frontend/dist`) is committed to this repo. `run.py`
  only tries to build it itself if `dist` is missing and Node happens to be installed.
- **A Portkey API key** with access to `gpt-6-luna` (the course key works). You'll need it before
  step 2 below.

## 1. Clone and install (~2 minutes)

macOS / Linux:

```bash
git clone <this-repo-url> gavel
cd gavel
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows (PowerShell):

```powershell
git clone <this-repo-url> gavel
cd gavel
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 2. Add your key (~1 minute)

Gavel looks for a `.env` file in the repo folder first, then **one level above it** — put your
real key one level above this repo, never inside it, so it's never at risk of being committed:

```
your-parent-folder/
  .env              <- put PORTKEY_API_KEY=your-course-key here, one line
  gavel/            <- this repo (what you just cloned)
```

The `.env` file should contain exactly:

```
PORTKEY_API_KEY=your-course-key
```

See [`.env.example`](.env.example) for the variable names (no real values are ever committed
there, or anywhere in this repo).

## 3. Run it (~10 seconds to start)

```bash
python run.py
```

This loads `.env`, picks a free port starting at 8000, starts the backend, and prints a URL like
`http://127.0.0.1:8000`. Open it in a browser.

## 4. Use the app (~2 minutes for a first look, longer for a full run)

1. Click **"Try the sample"** on the Start screen. Loads a synthetic policy and 24 sample club
   requests, then compiles rules (~5-10 seconds, one real model call) — no uploads needed.
2. On the **Rules** screen, review the proposed rules (each shows the exact policy quote and
   whether it verified) and click **"Approve all verified"** (or approve/reject individually).
3. Go to the **Run** tab and click **"Start run"**. A real run over 24-27 requests takes roughly
   30-60 seconds (parallelized Request Reader + Skeptic calls, one Policy Compiler call already
   done in step 1, one Drafter call per request that needs a question, one memo call).
4. Watch the agent nameplates and the live event feed while it runs. When it finishes, check
   **Review** (every line's verdict and citation), **Scenarios** (funding sliders), **Consistency**
   (last year's decisions vs. this year's rules), **Drafts** (committee questions + memo, and a CSV
   download), and **Cost** (real token/dollar totals).

### Using your own policy and requests

On the **Start** screen, instead of "Try the sample":
- Paste or upload (`.txt`) your own policy. Each rule paragraph needs to be on its own line,
  starting with a number, e.g. `3.1  Funds may not be used to purchase alcohol.`
- Paste (as JSON) or upload (`.txt`, `.html`, or `.json`) your own request. JSON needs `club`,
  `event_date`, `submitted_date`, `justification`, and a `lines` array (each line needs at least
  `description` and `amount`). See the Start screen's hints for the exact `.txt` format.

Then go to **Rules** to compile and approve, and **Run** to run it.

### Importing clubs, budgets, and many requests at once

The **Clubs** tab (reachable right away, no data load needed first) shows every registered club's
pre-approved budget and running balance (budget minus every allowed/reduced dollar from its latest
run; a negative balance means the club is over budget). Two import panels there let you:
- **Import clubs and budgets in bulk**: paste or upload (`.json`) an array of
  `{"name": ..., "category": ..., "pre_approved_budget": ...}` objects. Only `name` is required.
  Re-importing an existing name updates its budget in place (how you'd roll the registry to a new
  year) instead of creating a duplicate.
- **Import many requests at once**: paste or upload (`.json`) an array of request objects, same
  shape as a single request on the Start screen. Each row is imported independently, so one bad
  row's error is reported without blocking the rest.

The demo's 24 synthetic clubs are seeded automatically with their `last_year_allocated` figure from
`data/club_history.json` when you load the sample.

## Running the tests, benchmark, and safety test

All from the repo root, with the virtualenv active:

```bash
python -m pytest tests/            # ~20-80s (makes a handful of real, cheap model calls)
python -m backend.run_check        # ~1-2 min, runs the full pipeline over 24 requests and scores it
python -m backend.benchmark        # ~5-10 min, Mode A vs. Mode B x3 reps + 5 experiments
python -m safety_test              # ~1-2 min, the 6 safety test cases (prompt injection defenses)
```

Each of these reloads the database fresh (`python -m backend.load` is also available standalone)
and makes real model calls — expect a few cents of real API cost per full run, logged exactly in
the `usage` table / `/api/usage`.

## Repo layout

```
CONTEXT.md       — the project brief
PROMPTS/         — one prompt file per build step (the prompt log)
AI_prompts.md    — what happened at each step
harness.md       — the technical write-up (schema, tools, agents, routes, safety)
data/            — synthetic policy, requests, answer keys (do not edit)
tools/           — the data generator, reference rule engine, and evidence-generating scripts
evidence/        — manual baseline, benchmark, safety, cost, and fresh-clone evidence
backend/         — FastAPI app, the PydanticAI agents, the engine, CHAIR orchestration
mcp_server/      — the FastMCP server every agent's tools go through
frontend/        — React + Vite + TypeScript dashboard (frontend/dist is committed; built)
output/          — traces, smoke tests, and run artifacts
tests/           — automated tests (pytest)
safety_test.py   — the safety test suite (prompt injection defenses)
run.py           — one-command start
env_loader.py    — shared .env loader for the backend and the MCP server
```

## Troubleshooting

**"Missing required environment variable(s): PORTKEY_API_KEY"** — `.env` isn't where Gavel is
looking. It checks the repo folder first, then exactly one folder above it. Confirm the file is
named `.env` (not `.env.txt`) and contains a line like `PORTKEY_API_KEY=your-course-key` with no
quotes around the value.

**Nothing loads, or a different app answers at the printed URL** — `run.py` picks the first free
port starting at 8000; if something else was already using 8000 (another Gavel instance, or an
unrelated server), it'll pick 8001, 8002, etc., and print whichever one it actually bound. Use the
exact URL `run.py` prints, not a hardcoded `:8000`. If you want port 8000 specifically, stop
whatever else is using it first.

**`pip install` fails, or the app behaves strangely with cryptic errors** — check `python3
--version` is 3.11 or newer. On a machine with multiple Python versions installed, `python3` might
resolve to an older one; try `python3.11 -m venv .venv` (or whichever 3.11+ version you have)
explicitly when creating the virtualenv.
