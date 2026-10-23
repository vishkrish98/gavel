# Gavel harness

Technical reference, updated at every build step. Sections fill in as the matching step lands.

## Step log

| Step | What exists after this step |
| --- | --- |
| 00 | Skeleton: backend/, mcp_server/, frontend/, output/, tests/ folders; shared env_loader.py (checks repo folder then one level above); run.py (loads env, picks a free port, starts the backend, serves a placeholder page). |
| 01 | SQLite data layer at `data/gavel.db` (gitignored, created fresh on every loader run); loader `python -m backend.load` reads the policy, 24 real requests, 2 JSON safety requests, 1 HTML safety request (hidden-text aware), and 30 prior decisions (stripped of answer-key fields) into it. |

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

(filled in step02 — load_policy, list_rules, propose_rule, approve_rule, verify_quote, get_request, check_line, run_engine, consistency_report, allocate, explain_line, log_usage)

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
