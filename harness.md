# Gavel harness

Technical reference, updated at every build step. Sections fill in as the matching step lands.

## Step log

| Step | What exists after this step |
| --- | --- |
| 00 | Skeleton: backend/, mcp_server/, frontend/, output/, tests/ folders; shared env_loader.py (checks repo folder then one level above); run.py (loads env, picks a free port, starts the backend, serves a placeholder page). |
| 01 | SQLite data layer at `data/gavel.db` (gitignored, created fresh on every loader run); loader `python -m backend.load` reads the policy, 24 real requests, 2 JSON safety requests, 1 HTML safety request (hidden-text aware), and 30 prior decisions (stripped of answer-key fields) into it. |
| 02 | `mcp_server/server.py` (FastMCP, stdio): 12 deterministic tools over that data — policy/rule compilation, the rule engine, the consistency check, the water-filling optimizer, and token-usage logging. `tests/test_mcp.py` (18 tests, all passing) and `output/mcp_smoke.json` exercise every tool against real data, including the full 158/158 engine match and 6/30 consistency match using the answer key as a test fixture. |
| 03 | `evidence/engine_eval.json` (via `tools/make_engine_eval.py`): formal validation of the deterministic layer against the reference answer key, zero model calls. 158/158 lines match verdict+amount+rules exactly; `allocate` matches `data/optimizer_truth.json` to the cent across all 4 scenarios; `consistency_report` finds 6/30 inconsistent. |
| 04 | The agent team (`backend/agents.py`, `backend/chair.py`, `backend/models.py`, `backend/prompts/`). First step with real model calls. `python -m backend.run_check` runs the full pipeline over the 24 real requests and scores it: 100% rule recall/precision, 0 decoys turned into rules, 100% category accuracy, 100% verdict accuracy, exact dollar match (158/158), 100% consistency-report agreement with the step03 baseline, 10 Skeptic flags (0 of which were actual misclassifications). 61 model calls, 103,793 tokens, $0.016, run saved as `output/trace_run1.json`. |
| 05 | Token logging and cost: confirmed `log_usage` already logs the provider's real response fields (no change needed, inspected and documented below); `backend/pricing.py` now dated and cites the course Lecture 11 table; `GET /api/usage?run_id=` and `GET /api/runs` added to `backend/main.py`; `backend/projection.py` turns measured usage into unit costs and semester projections, all assumptions in one labeled block, output at `evidence/cost_model.md`. |

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

Rule types, eval_line order, and the optimizer are documented under "MCP tools" above
(`backend/engine.py` is shared by both the MCP server and this validation).

**Step03 formal validation** (`evidence/engine_eval.json`, `python -m tools.make_engine_eval`,
zero model calls — the 12 rules and all line facts are a labeled test fixture, not agent output):

| Check | Result |
| --- | --- |
| 158 real lines, verdict + allowed_amount + rule ids all match `data/requests_truth.json` | 158/158 |
| `backend.engine.allocate` vs `data/optimizer_truth.json`, all 4 scenarios | exact to the cent |
| `consistency_report` vs `data/prior_decisions.json` | 6/30 inconsistent (all 30 matched) |
| Tokens used | 0 (deterministic engine only) |

## Agents

All model-backed agents share one model config (`backend/agents.py`): `gpt-6-luna` through
Portkey, `OpenAIResponsesModel` (the `/v1/responses` endpoint — chat completions rejects tool
calls when reasoning effort is set), `openai_reasoning_effort="low"`, 60s per-call timeout. Every
agent's toolset is filtered MCP tools from `mcp_server/server.py` — no agent has a private data
path. Prompts live as markdown in `backend/prompts/`.

| Agent | Model? | Tools | What it does |
| --- | --- | --- | --- |
| **CHAIR** | No — plain Python (`backend/chair.py`, `ChairRun` / `run_full_pipeline`) | calls the others | Orchestrates one run in a fixed order: compile rules once, read every request in parallel, run the Skeptic on lines the engine would currently allow in full, persist verdicts, run the consistency report and optimizer (code), draft questions and a memo, record run status. |
| **Policy Compiler** | Yes | `load_policy`, `propose_rule` | Reads all 16 paragraphs, proposes a rule (type + params + exact quote) for each one that's binding and machine-checkable; skips guidance/info paragraphs. `propose_rule` verifies the quote in the same call. |
| **Request Reader** | Yes | `get_request` | Per request (24 run in parallel, semaphore 8): classifies every line into one of 12 categories and extracts headcount/qty/nights/unit_cost from description + amount alone. |
| **Skeptic** | Yes | `get_request` | Reviewed only on lines whose *preliminary* engine verdict (using the Reader's facts) is `allowed` — CONTEXT.md's "for each line the Reader marked allowed." Batched per request, not per line. May flag a line with a reason; never changes a category or fact itself. |
| **Engine** | No — code | n/a | `backend/engine.py` via `run_engine`/`check_line` (step02/03). |
| **Optimizer** | No — code | n/a | `backend/engine.allocate` via the `allocate` tool (step02/03). |
| **Drafter** | Yes (two agents: questions, memo) | none (CHAIR resolves everything into the prompt first) | Per request with a needs_docs line, a Skeptic-flagged line, or a reduction to ≤50% of the requested amount: drafts one question per such line, citing the rule and quote (via `explain_line`). One more call drafts a whole-pot memo from aggregate totals. Both saved to the new `drafts` table with `status='awaiting_approval'` — nothing is exported without a human approval click (not wired up until a later step's UI). |

**Run flow** (`run_full_pipeline`, `backend/chair.py`):
1. `compile_rules()` — one Policy Compiler call; in `benchmark_mode` (used by `run_check`), a
   paragraph's proposed rule auto-approves (`approve_rule`, `by="benchmark-auto-approve"`) only if
   it's the *only* rule proposed for that paragraph and its quote verified — "verified AND match
   nothing else." Logged as `auto_approved_for_benchmark`. Multiple proposals for one paragraph are
   left for a human (`rule_needs_human_review`) instead of guessing which one is right.
2. `read_all_requests()` — Request Reader per request, `asyncio.gather` under a semaphore of 8;
   writes category/headcount/qty/nights/unit_cost straight into `lines` (the Reader itself never
   writes — it only calls the read-only `get_request` tool, per CONTEXT.md hard rule 4; CHAIR does
   the persistence after getting the agent's structured output back).
3. `_preliminary_allowed_lines()` — one `run_engine` call per request (code) to find which lines
   are currently `allowed` with nothing stopping them; those are what the Skeptic reviews.
4. `run_skeptic()` — Skeptic per request (batched, not per line — much cheaper and CONTEXT.md
   doesn't require per-line calls), semaphore of 8.
5. `persist_verdicts()` — final `run_engine` pass per request (identical to the preliminary pass,
   since the Skeptic never changes a fact), inserted into `verdicts` with `flagged_for_review` from
   the Skeptic. This is the first point a real `run_id` exists, so it's also the first point
   verdicts get persisted (step02 left `check_line`/`run_engine` as pure, non-persisting reads).
6. `consistency_report()` and `allocate()` — code, unchanged from step02/03.
7. `run_drafter()` — one Drafter-questions call per request that needs one, then one Drafter-memo
   call for the whole run. Drafts saved to the `drafts` table.
8. `finalize_run()` — updates `runs.status`/`finished_at`.

**Limits, enforced on every single agent call** (`ChairRun._call_agent`): a wall-clock timeout
(`asyncio.wait_for`, 60s), a request limit and a per-call token cap (both via PydanticAI's
`UsageLimits` on that one call — this doubles as the "per-agent token cap"), and a whole-run token
cap of 400,000 tracked in Python across every call this run makes (checked before each call;
real run1 used 103,793 — nowhere near the cap). Hitting any of these raises `RunLimitHit`, which
`run_full_pipeline` catches, sets `runs.status='limit_hit'` with the reason recorded, and returns
cleanly instead of crashing.

**`python -m backend.run_check`** (`backend/run_check.py`) runs the full pipeline over the 24 real
requests and scores it against the answer key — rule recall/precision, quote validity, decoy
paragraphs wrongly turned into rules, category accuracy per category, verdict accuracy (overall
and per type), allowed-dollar accuracy, Skeptic flags vs. actual errors, and consistency-report
agreement against the step03 true-fixture baseline. Full real numbers from `run1`
(`evidence/run_check.json`, trace in `output/trace_run1.json`, **not fixed, reported as-is**):

| Metric | Result |
| --- | --- |
| Rule recall / precision | 12/12 (1.0 / 1.0) |
| Decoy paragraphs turned into rules | 0 |
| Quote validity rate | 12/12 proposed, 0 rejected (1.0) |
| Category accuracy, overall and every one of the 12 categories | 1.0 |
| Verdict accuracy, overall and every verdict type | 1.0 |
| Lines with both verdict AND allowed-dollar amount exactly correct | 158/158 |
| Total allowed: computed vs. truth | $57,273.00 vs. $57,273.00 (exact) |
| Skeptic: lines flagged / actual misclassifications caught | 10 flagged, 0 were real category errors |
| Consistency-report agreement with step03 baseline | 30/30 decisions agree (6/30 inconsistent both ways) |
| Model calls / tokens / cost / wall-clock (sum) | 61 calls, 103,793 tokens, $0.016, ~248s |

These numbers are real and better than expected going in — plausible because the synthetic line
descriptions are template-generated and mostly unambiguous once you catch the euphemisms the
prompt calls out by name (confirmed by spot-checking: "Pre-paid visa cards..." → `gift_card`,
"Signature cocktails for gala..." → `alcohol`, both correct). The Skeptic's 10 flags were all
reasonable caution (vague descriptions, high per-person costs) rather than real errors — worth
noting honestly as a 0%-precision-on-the-metric-as-defined result rather than claiming it "works."
Nothing was tuned to produce these numbers; per the step04 instruction, accuracy was not adjusted.

## Token logging / cost model

**Raw provider fields, inspected directly (not estimated).** Every model call returns a PydanticAI
`RunUsage`/`RequestUsage` object built straight from the Portkey/OpenAI Responses API response.
Printed one raw example (`dataclasses.asdict(result.usage)`):

```
{'input_tokens': 19, 'cache_write_tokens': 0, 'cache_read_tokens': 0, 'output_tokens': 5,
 'input_audio_tokens': 0, 'cache_audio_read_tokens': 0, 'output_audio_tokens': 0,
 'audio_seconds': 0, 'details': {'reasoning_tokens': 0}, 'cost': None, 'requests': 1, 'tool_calls': 0}
```

`ChairRun._call_agent` (`backend/chair.py`) maps these straight through to `log_usage` with no
estimation or renaming games: `cached_tokens` = `cache_read_tokens`, `cache_write_tokens` =
`cache_write_tokens`, `reasoning_tokens` = `details["reasoning_tokens"]` (nested there because the
Responses API reports it as a sub-field of output tokens, not top-level). `total_tokens` =
`input_tokens + output_tokens` (reasoning tokens are already counted inside `output_tokens` by the
provider, not additional on top of it).

**Pricing** (`backend/pricing.py`, single source of truth per CONTEXT.md): gpt-6-luna via Portkey,
$0.10 / $0.01 / $0.125 / $0.50 per 1M input/cached/cache-write/output tokens — course Lecture 11
table, dated 2026-10-23 in the file itself so a price change is a one-line diff with a date to
check against.

**API routes** (`backend/main.py`): `GET /api/usage?run_id=` (with a run_id: that run's totals
broken down by agent, plus the run's grand total; without one: every run's grand total, for
comparing runs) and `GET /api/runs` (every run's status/mode/timestamps with its usage total
attached).

**Cost model** (`backend/projection.py` → `evidence/cost_model.md`): every assumption lives in one
`ASSUMPTIONS` dict at the top of the file — nothing else in it hardcodes a number that isn't
either an assumption or pulled from the measured `usage`/`verdicts` tables for a real run.
Unit costs (measured, run1): compiling the policy once **$0.000751**, the whole-pot memo once
**$0.000124**, per request (Reader + Skeptic + drafted questions) **$0.000632**, per line item
**$0.000096**. Semester projections: 24 clubs (measured) **$0.016**; 150 clubs (**assumption**)
**$0.096**; a platform of 1,000 institutions, each compiling its own policy and averaging 24 clubs
(**assumption**) **$16.04**. Human comparison (**assumption**: 20 minutes/request at $20/hour) is
**$6.67/request** manually vs. **$0.00063/request** for Gavel's first-pass packet — framed
honestly in the file itself as the cost of producing the packet, not a claim that it replaces the
committee's actual decision (CONTEXT.md hard rule 10).

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
- Step04: CHAIR is plain Python orchestration, not a PydanticAI `Agent` with delegation tools
  (unlike the reference chassis's Boss). The pipeline order is entirely fixed (compile once, read
  in parallel, Skeptic, engine, consistency, optimizer, draft) — nothing about it needs a model to
  decide, so spending a model call on an "orchestrator" that would just always do the same thing in
  the same order would be pure token cost with no judgment behind it.
- Step04: Skeptic runs on lines whose *preliminary engine verdict* (using the Reader's facts) is
  `allowed` — CONTEXT.md's AGENTS section says "for each line the Reader marked allowed," which
  this matches more literally than the step04 prompt's looser "permissive category" phrasing
  (under that reading, alcohol/gift_card lines are already maximally restricted — denied — so
  there's nothing more restrictive left to find for them).
- Step04: Skeptic and Drafter-questions are batched per request (one call reviewing/drafting
  several lines at once), not per line — matches how the Request Reader is explicitly specified
  ("runs requests in parallel"), and keeps call count to ~61 for the whole run instead of one call
  per line (158+) for no accuracy benefit CONTEXT.md asks for.
- Step04: "verified AND match nothing else" (the benchmark auto-approve condition) is implemented
  as "exactly one rule was proposed for this paragraph, and its quote verified." Multiple
  candidate rules proposed for the same paragraph are left for a human instead of auto-approving
  one arbitrarily.
- Step04: added a `drafts` table (id, run_id, request_id, kind, content_json, status,
  created_at) — not in the step01 schema list, but the Drafter's output (committee questions, the
  memo) has nowhere else to live. `status` starts `awaiting_approval`; nothing moves to `approved`
  until a human approval route exists (a later step).
- Step04: "large reduction" (one of three reasons the Drafter asks about a line, alongside
  needs_docs and a Skeptic flag) is defined as allowed_amount ≤ 50% of the requested amount.
  CONTEXT.md doesn't specify a threshold; 50% is the simplest clearly-large cut.
- Step05: the "platform serving 1,000 institutions" projection assumes each institution compiles
  its own policy once and averages 24 clubs (our sample size), i.e. policies are NOT shared across
  institutions — each institution's compile cost is paid once, not amortized across the platform.
  This is the more realistic (and more conservative/expensive) assumption since different
  institutions would have different real policies, not one shared synthetic one.
- Step05: "cost per request" (used for the semester/platform projections) includes Reader +
  Skeptic + drafted-questions costs but NOT the one-time policy-compile or whole-pot-memo costs —
  those scale with the number of runs/semesters, not the number of requests, so folding them into
  a per-request figure would make the projection wrong at any scale other than exactly 24 requests.
- Step04: the whole-run 400,000-token cap is tracked manually in Python (summed after each call),
  not passed as a single shared `usage=` object into every PydanticAI call — PydanticAI's
  `UsageLimits` checks against whatever `usage` object you pass it, and a per-call fresh usage
  object is what makes the *per-agent* token cap (via `usage_limits.total_tokens_limit` on that
  one call) meaningful; sharing one cumulative object across every call would only ever enforce
  the whole-run cap, not a per-call one. Doing both needed two separate mechanisms.
