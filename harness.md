# Gavel harness

Technical reference, updated at every build step. Sections fill in as the matching step lands.

## Step log

| Step | What exists after this step |
| --- | --- |
| 00 | Skeleton: backend/, mcp_server/, frontend/, output/, tests/ folders; shared env_loader.py (checks repo folder then one level above); run.py (loads env, picks a free port, starts the backend, serves a placeholder page). |
| 01 | SQLite data layer at `data/gavel.db` (gitignored, created fresh on every loader run); loader `python -m backend.load` reads the policy, 24 real requests, 2 JSON safety requests, 1 HTML safety request (hidden-text aware), and 30 prior decisions (stripped of answer-key fields) into it. |
| 02 | `mcp_server/server.py` (FastMCP, stdio): 12 deterministic tools over that data — policy/rule compilation, the rule engine, the consistency check, the water-filling optimizer, and token-usage logging. `tests/test_mcp.py` (18 tests, all passing) and `output/mcp_smoke.json` exercise every tool against real data, including the full 158/158 engine match and 6/30 consistency match using the answer key as a test fixture. |

## Data tables

SQLite at `data/gavel.db` (gitignored; `python -m backend.load` creates it fresh each run — see
`backend/db.py` for the full schema, `backend/load.py` for the loader, `backend/hidden_html.py`
for the Q27 hidden-text parser).

| Table | Columns | Notes |
| --- | --- | --- |
| `policy_paragraphs` | para_id (PK), text, kind | `kind` loaded as NULL — classifying a paragraph as rule/guidance/info is the Policy Compiler's job (step04), not the loader's. Deciding this at load time would leak which paragraphs are decoys. |
| `rules` | id (PK), para_id, type, params_json, quote, quote_verified, status (proposed/approved/rejected), approved_by | Empty until step04 (Policy Compiler proposes, a human approves). |
| `requests` | id (PK), club, event_date, submitted_date, justification, source | `source` is the file it came from: `requests_input.json`, `safety_requests.json`, or `safety_request_hidden.html`. |
| `lines` | id (PK), request_id (FK), description, amount, docs_json, already_purchased, category, headcount, qty, nights, unit_cost, quarantined | category/headcount/qty/nights/unit_cost load as NULL — classifying each line is the Request Reader's job (step04). `quarantined` defaults to 0; the safety step (step07) sets it. |
| `verdicts` | run_id, line_id (FK), verdict, allowed_amount, rules_json, explanation, flagged_for_review | PK (run_id, line_id). Empty until step03 (Engine). |
| `runs` | id (PK), started_at, finished_at, status, mode | Empty until step04. |
| `allocations` | run_id, scenario, club, amount | Empty until step06 (Optimizer/benchmark). Club facts (pot, last-year utilization) are read directly from `data/club_history.json`, not from a DB table — no table for club history is in the step01 schema. |
| `prior_decisions` | id (PK), club, description, requested, approved, docs_json, term | Loaded WITHOUT `inconsistent` and `policy_allowed` — those are answer-key fields in `data/prior_decisions.json` used only by step03's consistency-check scoring, never by anything an agent can see. `docs_json`/`term` kept as extra non-answer-key context (ambiguous call, see below). |
| `usage` | run_id, agent, model, input_tokens, cached_tokens, cache_write_tokens, output_tokens, reasoning_tokens, total_tokens, seconds, cost_usd, created_at | Empty until step05 (token logging). |
| `audit` | id (PK autoincrement), run_id, ts, event, detail_json | Append-only: no UPDATE/DELETE statement against this table exists anywhere in the codebase. Empty until step02+. |

Loaded counts (from `python -m backend.load`): 16 policy paragraphs; 24 real requests (158
lines) + 2 JSON safety requests (16 lines: Q25, Q26) + 1 HTML safety request (5 lines: Q27) = 27
requests / 179 lines; 30 prior decisions; 2 hidden-text flags in the Q27 HTML (one font-size:0
span, one white-on-white span — both carry the same injection text, recorded but not stripped,
for step07 to use). `club_history.json` (24 clubs, $40,000 pot) is read and validated at load
time but not persisted (see above).

## MCP tools

`mcp_server/server.py`, registered as `gavel` in `.mcp.json` (stdio, FastMCP). All 12 tools are
deterministic — no model calls anywhere in this file (CONTEXT.md hard rule 4: agents touch data
only through these tools).

| Tool | Signature | What it does |
| --- | --- | --- |
| `load_policy` | `()` | Every policy paragraph. `kind` is always NULL here — classifying rule/guidance/info is the Policy Compiler's job (step04), never this tool's. |
| `list_rules` | `(status=None)` | Rules filtered by status, or all. |
| `verify_quote` | `(text_id, quote)` | True only if `quote` is an exact substring of that paragraph's text after normalizing whitespace and curly quotes (`backend/quotes.py`). Never fuzzy. |
| `propose_rule` | `(para_id, type, params, quote)` | Verifies the quote in the same call. Verified → stored `proposed` (awaiting `approve_rule`). Not verified → stored `rejected` with an audit entry (`reason: quote_not_found`) and never reaches a human. |
| `approve_rule` | `(rule_id, by)` | Human approval step. Refuses a rule whose quote was never verified. Only `approved` rules are used by the engine. |
| `get_request` | `(request_id)` | One request with all its lines. |
| `check_line` | `(request_id, line_id)` | Evaluates the whole request's lines in order (semester cap needs the running total) and returns this one line's verdict/allowed_amount/rules. |
| `run_engine` | `(request_id)` | `check_line` over every line of a request. |
| `explain_line` | `(request_id, line_id)` | The verdict plus the exact policy quote (via the rule's `para_id`) for every rule it hit. |
| `consistency_report` | `()` | Matches each of the 30 `prior_decisions` to the current line it was cloned from (key: **club** + description + requested amount + docs — description/amount/docs alone collides 36 times across different clubs in the real data, e.g. many clubs separately request "Venue rental for event" for exactly $250 with no docs), re-evaluates it with the engine, flags a mismatch as inconsistent. |
| `allocate` | `(pot, alpha)` | Water-filling optimizer (`backend/engine.allocate`, ported verbatim from `tools/make_funding_data.py`). `allowed` per club comes from running the engine over that club's real request (`source='requests_input.json'` only — the three safety-case clubs aren't part of the funding pool); `utilization` is read directly from `data/club_history.json` (no DB table for it; see step01). |
| `log_usage` | `(run_id, agent, input_tokens, cached_tokens, cache_write_tokens, output_tokens, reasoning_tokens, seconds, model=...)` | Writes a `usage` row; cost computed from the single pricing config `backend/pricing.py` (gpt-6-luna: $0.10/$0.01/$0.125/$0.50 per 1M input/cached/cache-write/output tokens). |

The engine itself (`backend/engine.py`) is generalized over whatever rules are currently
`approved` (type + JSON params), not a hardcoded R01-R12 list — real rules only exist once the
Policy Compiler proposes them and a human approves them (step04). The fixed rule-type check
order mirrors `tools/make_funding_data.py`'s `eval_line` exactly: deadline → retroactive_prohibit
→ prohibited_category → unit_threshold_prohibit → unit_cap → per_person_cap → per_night_cap →
event_cap → requires_docs → semester_cap (applied last, across a request's lines in the order
they're stored).

Verified against the real answer key (test fixture, not yet the real agents — see
`tests/test_mcp.py` and `output/mcp_smoke.json`):
- 12 true rules proposed + approved through the real `propose_rule`/`approve_rule` tools.
- TRUE line facts from `data/requests_truth.json` written directly into `lines` (stand-in for
  the step04 Request Reader, which doesn't exist yet).
- `run_engine` reproduces **158/158** real lines' verdict and allowed_amount exactly.
- `consistency_report` finds **6/30** inconsistent, matching all 30 prior decisions.
- `backend.engine.allocate` matches `data/optimizer_truth.json` to the cent across all 4 scenarios.
- A verified quote and a fake, rejected quote are both recorded in `output/mcp_smoke.json`, along
  with how every call was made (in-process, direct Python calls to the same functions FastMCP
  registers — not round-tripped over the stdio transport for this smoke test; see that file's
  own `how_these_calls_were_made` field).

## Engine

(filled in step03 — rule types, eval_line order, optimizer)

## Agents

(filled in step04 — CHAIR, POLICY COMPILER, REQUEST READER, SKEPTIC, ENGINE, OPTIMIZER, DRAFTER)

## Token logging / cost model

(filled in step05)

## Benchmark

(filled in step06 — Mode A vs Mode B)

## Safety rules

(filled in step07 — prompt injection defenses, Q25/Q26/Q27 handling)

## API routes

(filled in step08a)

## Frontend

(filled in step08b)

## Ambiguous calls made along the way

- Step00: used one top-level `env_loader.py` (not inside backend/ or mcp_server/) as the shared
  env-loader, since CONTEXT.md step00 prompt calls for "one shared env-loader helper used by the
  backend and the MCP server" and both are separate top-level packages — a root-level module both
  can import after adding ROOT to sys.path (same pattern the reference chassis uses) is simpler
  than making one of them import from the other.
- Step00: run.py does not launch an MCP server subprocess yet — mcp_server/ doesn't exist until
  step02, and per the reference chassis pattern, agents spawn it over stdio themselves rather than
  run.py managing it as a separate long-running process.
- Step01: `prior_decisions` keeps two columns (`docs_json`, `term`) beyond the minimum column list
  given in the step01 prompt. Neither is an answer-key field (those are `inconsistent` and
  `policy_allowed`, which are NOT loaded); `docs_json` lets step03's consistency check re-derive
  what the policy would allow (e.g. whether a >$500 purchase had 3 quotes) without re-reading the
  raw JSON file outside the DB layer.
- Step01: `policy_paragraphs.kind` and `lines.category/headcount/qty/nights/unit_cost` load as
  NULL on purpose — those are exactly the judgments the Policy Compiler and Request Reader agents
  make in step04. Pre-filling them at the data layer would leak the answer key into the agents'
  inputs.
- Step01: `data/club_history.json` is read and validated (fails loudly if `pot`/`clubs` are
  missing) but not written to its own table — the step01 schema list has no table for it, and the
  optimizer (step06) is expected to read it directly from `data/`, matching how
  `tools/make_funding_data.py`'s reference engine does it.
- Step02: `propose_rule` generates its own rule ids (`RULE-xxxxxxxx`, random), not the truth
  file's `R01`..`R12` — those are answer-key labels for `tools/make_funding_data.py`'s fixed rule
  set, not IDs the real Policy Compiler is expected to reproduce. The test fixture keeps a mapping
  from truth id to generated id to compare which rules fired.
- Step02: `consistency_report` matches a prior decision to a current line by **(club,
  description, requested amount, docs)**, not description/amount/docs alone — the latter has 36
  collisions in the real data (many clubs coincidentally request identical-looking line items,
  e.g. "Venue rental for event" for exactly $250 with no docs). Club disambiguates every case in
  this dataset; CONTEXT.md says only "the same category and facts," so this is the simplest key
  that's actually unique.
- Step02: `check_line`/`run_engine`/`explain_line` compute and return results on every call; they
  do not write to the `verdicts` table. No `run_id` exists yet to attach a verdict to (the `runs`
  table is still empty — that starts in step04 when the CHAIR orchestrates a real run). Persisting
  verdicts is deferred to whichever step first has a real run to attach them to.
- Step02: `run.py` still does not spawn `mcp_server/server.py` as a long-running subprocess, even
  though it now exists — per the reference chassis pattern (CONTEXT.md step00 note), agents will
  spawn their own stdio connection to it in step04, the same way `backend/agents.py` does in the
  reference chassis.
