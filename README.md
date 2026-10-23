# Gavel

Decision support for a student-government funding committee. Turns a funding policy into
machine-checkable rules (each tied to a quote from the policy, verified by code and approved by
a human), reads every club budget request line, applies the rules in code for a verdict and
citation, checks last year's decisions for inconsistency, and runs funding scenarios with a
deterministic optimizer. Gavel recommends and explains; the committee decides.

This README is a work in progress through the build (full fresh-clone instructions land in
step09 — see `PROMPTS/step09_readme_fresh_clone.md`). See [`harness.md`](harness.md) for the
technical write-up (data tables, MCP tools, agents, API routes, safety rules) as it fills in.

## Prerequisites

- Python 3.11+
- Node.js 20+ (needed starting at step08b, for the frontend)
- A Portkey API key with access to `gpt-6-luna`

## Setup

From the repo root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Gavel looks for a `.env` file in the repo folder first, then **one level above it**. Put your
real key one level above this repo (never inside it):

```
your-parent-folder/
  .env              <- PORTKEY_API_KEY=your-course-key goes here
  gavel/            <- this repo
```

See `.env.example` for the variable names (no real values are ever committed).

## Running

```bash
python run.py
```

This loads `.env`, picks a free port starting at 8000, and starts the backend. It prints the
URL to open. The frontend is not built yet (lands in step08b) — until then you'll see a
placeholder page confirming the backend is up.

## Repo layout

```
CONTEXT.md     — the project brief
PROMPTS/       — one prompt file per build step (the prompt log)
AI_prompts.md  — what happened at each step
data/          — synthetic policy, requests, answer keys (do not edit)
tools/         — data generator and reference rule engine
evidence/      — manual baseline, benchmark, safety, and cost evidence
backend/       — FastAPI app and (from step04) the PydanticAI agents
mcp_server/    — the FastMCP server (from step02)
frontend/      — the React + Vite + TypeScript dashboard (from step08b)
output/        — traces, smoke tests, and run artifacts
tests/         — automated tests
run.py         — one-command start
env_loader.py  — shared .env loader for backend and MCP server
```
