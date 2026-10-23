# Gavel harness

Technical reference, updated at every build step. Sections fill in as the matching step lands.

## Step log

| Step | What exists after this step |
| --- | --- |
| 00 | Skeleton: backend/, mcp_server/, frontend/, output/, tests/ folders; shared env_loader.py (checks repo folder then one level above); run.py (loads env, picks a free port, starts the backend, serves a placeholder page). |

## Data tables

(filled in step01 — policy paragraphs, requests/line items, club history, prior decisions, safety requests)

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
