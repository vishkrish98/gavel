"""FastAPI backend for Gavel.

Run with `python run.py` from the repo root (never `uvicorn backend.main:app` directly in
normal use, since run.py is what loads .env and picks a free port). Step00: this just proves
the env-loader and serves a placeholder page. Real routes (policy, requests, engine, agents,
scenarios) are added in step08a; the built frontend is mounted here once step08b exists.
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
ROOT = BACKEND_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from typing import Optional

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from backend.db import get_connection
from env_loader import require_env

require_env(["PORTKEY_API_KEY"])

app = FastAPI(title="Gavel")

FRONTEND_DIST = ROOT / "frontend" / "dist"

PLACEHOLDER_HTML = """<!doctype html>
<html>
<head><title>Gavel</title></head>
<body style="font-family: sans-serif; max-width: 640px; margin: 4rem auto;">
<h1>Gavel is running</h1>
<p>Backend is up. The frontend is not built yet (that lands in step08b).</p>
<p>Health check: <a href="/health">/health</a></p>
</body>
</html>"""


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _usage_totals(rows: list) -> dict:
    keys = ["input_tokens", "cached_tokens", "cache_write_tokens", "output_tokens", "reasoning_tokens", "total_tokens", "seconds", "cost_usd"]
    totals = {k: 0 for k in keys}
    for row in rows:
        for k in keys:
            totals[k] += row[k]
    totals["calls"] = len(rows)
    return totals


@app.get("/api/usage")
def get_usage(run_id: Optional[str] = None) -> dict:
    """Totals per agent and per run. With run_id: that run's totals broken down by agent, plus
    the run's grand total. Without run_id: every run's grand total, for comparing runs."""
    conn = get_connection()
    if run_id is not None:
        rows = [dict(r) for r in conn.execute("SELECT * FROM usage WHERE run_id = ? ORDER BY created_at", (run_id,))]
        conn.close()
        by_agent: dict[str, list] = {}
        for row in rows:
            by_agent.setdefault(row["agent"], []).append(row)
        return {
            "run_id": run_id,
            "by_agent": {agent: _usage_totals(agent_rows) for agent, agent_rows in by_agent.items()},
            "total": _usage_totals(rows),
        }
    run_ids = [r["run_id"] for r in conn.execute("SELECT DISTINCT run_id FROM usage ORDER BY run_id")]
    result = []
    for rid in run_ids:
        rows = [dict(r) for r in conn.execute("SELECT * FROM usage WHERE run_id = ?", (rid,))]
        result.append({"run_id": rid, **_usage_totals(rows)})
    conn.close()
    return {"runs": result}


@app.get("/api/runs")
def get_runs() -> list[dict]:
    """Every run's status/mode/timestamps, with its usage total attached."""
    conn = get_connection()
    runs = [dict(r) for r in conn.execute("SELECT * FROM runs ORDER BY started_at DESC")]
    for run in runs:
        rows = [dict(r) for r in conn.execute("SELECT * FROM usage WHERE run_id = ?", (run["id"],))]
        run["usage_total"] = _usage_totals(rows)
    conn.close()
    return runs


if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
else:

    @app.get("/", response_class=HTMLResponse)
    def placeholder() -> str:
        return PLACEHOLDER_HTML
