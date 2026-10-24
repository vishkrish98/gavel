"""FastAPI backend for Gavel.

Run with `python run.py` from the repo root (never `uvicorn backend.main:app` directly in
normal use, since run.py is what loads .env and picks a free port). The built frontend is
mounted here once step08b exists; until then, GET / serves a placeholder page.
"""

from __future__ import annotations

import asyncio
import csv
import io
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
ROOT = BACKEND_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pydantic_ai.usage import UsageLimitExceeded, UsageLimits

import mcp_server.server as srv
from backend import agents, audit, chair
from backend.db import get_connection
from backend.load import load_policy_text_into_db, main as reload_demo_data
from backend.requests_intake import RequestValidationError, insert_request, parse_uploaded_request
from env_loader import require_env

require_env(["PORTKEY_API_KEY"])

app = FastAPI(title="Gavel")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Last resort: a newcomer should see a plain-English message, never a raw stack trace."""
    return JSONResponse(status_code=500, content={"detail": f"Unexpected server error: {exc}"})

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


def _agent_family(agent_name: str) -> str:
    return agent_name.split(":", 1)[0]


# ---------------------------------------------------------------------------
# Policy: upload/paste, compile, approve/reject
# ---------------------------------------------------------------------------
# GET /api/policy/paragraphs, GET /api/rules, GET /api/requests, and GET /api/requests/{id} below
# are small read-only additions discovered while building the frontend (step08b) -- step08a's
# route list didn't include them, but the Rules screen needs every paragraph (to show decoys as
# "not a rule") and the Review screen needs to list/open requests. Thin wrappers over existing
# code (srv.load_policy, srv.list_rules, srv.get_request), nothing new underneath.


@app.get("/api/policy/paragraphs")
def list_policy_paragraphs() -> list[dict]:
    return srv.load_policy()


@app.get("/api/rules")
def list_rules_route(status: Optional[str] = None) -> list[dict]:
    return srv.list_rules(status=status)


@app.get("/api/requests")
def list_requests() -> list[dict]:
    conn = get_connection()
    rows = [dict(r) for r in conn.execute("SELECT * FROM requests ORDER BY rowid")]
    for row in rows:
        row["line_count"] = conn.execute("SELECT COUNT(*) FROM lines WHERE request_id = ?", (row["id"],)).fetchone()[0]
    conn.close()
    return rows


@app.get("/api/requests/{request_id}")
def get_request_route(request_id: str) -> dict:
    result = srv.get_request(request_id)
    if not result["found"]:
        raise HTTPException(404, f"No request with id {request_id!r}.")
    return result


@app.post("/api/policy")
async def upload_policy(file: Optional[UploadFile] = File(None), text: Optional[str] = Form(None)) -> dict:
    """Paste the policy text (`text` form field) or upload a .txt file (`file`). Replaces
    whatever policy was loaded before, and clears any rules proposed against the old one --
    rules are tied to specific paragraph ids/text that no longer apply."""
    if file is not None:
        content = (await file.read()).decode("utf-8", errors="replace")
    elif text is not None:
        content = text
    else:
        raise HTTPException(400, "Provide either a 'file' upload (.txt) or a 'text' form field with the policy text.")

    conn = get_connection()
    conn.execute("DELETE FROM rules")
    conn.execute("DELETE FROM policy_paragraphs")
    count = load_policy_text_into_db(conn, content)
    conn.commit()
    conn.close()
    if count == 0:
        raise HTTPException(
            400,
            "No policy paragraphs found. Each paragraph must be on its own line starting with a "
            "number like '3.1  Funds may not be used to purchase alcohol.'",
        )
    return {"paragraphs_loaded": count}


@app.post("/api/policy/compile")
async def compile_policy() -> dict:
    """Runs the real Policy Compiler agent. Returns every proposed rule (verified or not) --
    nothing is approved yet; use POST /api/rules/{id}/approve or /api/rules/approve-all-verified."""
    conn = get_connection()
    paragraph_count = conn.execute("SELECT COUNT(*) FROM policy_paragraphs").fetchone()[0]
    conn.close()
    if paragraph_count == 0:
        raise HTTPException(400, "No policy loaded yet. POST /api/policy first, or POST /api/demo/load for the sample policy.")

    try:
        result = await asyncio.wait_for(
            agents.policy_compiler_agent.run(
                "Compile the policy into rules now.", usage_limits=UsageLimits(request_limit=40, total_tokens_limit=60_000)
            ),
            timeout=60,
        )
    except asyncio.TimeoutError as exc:
        raise HTTPException(504, "Policy compilation timed out after 60s. Try again.") from exc
    except UsageLimitExceeded as exc:
        raise HTTPException(502, f"Policy compilation hit its token/request limit: {exc}") from exc

    return {"summary": result.output.model_dump(), "rules": srv.list_rules()}


class ApproveRuleRequest(BaseModel):
    by: str


@app.post("/api/rules/{rule_id}/approve")
def approve_rule_route(rule_id: str, body: ApproveRuleRequest) -> dict:
    result = srv.approve_rule(rule_id, body.by)
    if not result["approved"]:
        raise HTTPException(400, f"Could not approve rule {rule_id!r}: {result['reason']}.")
    return result


class RejectRuleRequest(BaseModel):
    by: str
    reason: Optional[str] = None


@app.post("/api/rules/{rule_id}/reject")
def reject_rule_route(rule_id: str, body: RejectRuleRequest) -> dict:
    result = srv.reject_rule(rule_id, body.by, body.reason)
    if not result["rejected"]:
        raise HTTPException(404, f"Could not reject rule {rule_id!r}: {result['reason']}.")
    return result


@app.post("/api/rules/approve-all-verified")
def approve_all_verified_route(body: ApproveRuleRequest) -> dict:
    """The demo's "approve all verified" one-click action -- still an explicit human call,
    just applied to every currently-proposed, quote-verified rule at once."""
    return srv.approve_all_verified_rules(body.by)


# ---------------------------------------------------------------------------
# Requests: paste or upload txt/html/json; the zero-upload demo
# ---------------------------------------------------------------------------


@app.post("/api/requests")
async def create_request(request: Request) -> dict:
    """Send either multipart/form-data with a 'file' field (.txt, .html, or .json), or
    application/json with the request object directly (club, event_date, submitted_date,
    justification, lines -- same shape as data/requests_input.json's entries)."""
    content_type = request.headers.get("content-type", "")
    conn = get_connection()
    try:
        if content_type.startswith("multipart/form-data"):
            form = await request.form()
            upload = form.get("file")
            if upload is None or not hasattr(upload, "filename"):
                raise RequestValidationError("No 'file' field found in the multipart upload.")
            content = await upload.read()
            parsed = parse_uploaded_request(upload.filename, content)
            request_id, line_count = insert_request(conn, parsed, source=f"upload:{upload.filename}")
        elif content_type.startswith("application/json"):
            payload = await request.json()
            if not isinstance(payload, dict):
                raise RequestValidationError("JSON body must be a single request object, not a list.")
            request_id, line_count = insert_request(conn, payload, source="api:paste")
        else:
            raise RequestValidationError(
                "Send multipart/form-data with a 'file' field (.txt/.html/.json), or "
                "application/json with the request object directly."
            )
    except RequestValidationError as exc:
        raise HTTPException(400, str(exc)) from exc
    finally:
        conn.close()
    return {"request_id": request_id, "lines_loaded": line_count}


@app.post("/api/demo/load")
async def demo_load() -> dict:
    """Loads the bundled sample policy, 24 requests, club history, and prior decisions in one
    call -- zero uploads needed to try the app. Also runs the real Policy Compiler so there's
    something to approve; nothing is auto-approved (see POST /api/rules/approve-all-verified)."""
    reload_demo_data()
    try:
        result = await asyncio.wait_for(
            agents.policy_compiler_agent.run(
                "Compile the policy into rules now.", usage_limits=UsageLimits(request_limit=40, total_tokens_limit=60_000)
            ),
            timeout=60,
        )
        compiled, summary = True, result.output.model_dump()
    except (asyncio.TimeoutError, UsageLimitExceeded) as exc:
        compiled, summary = False, {"error": str(exc)}

    conn = get_connection()
    counts = {
        "policy_paragraphs": conn.execute("SELECT COUNT(*) FROM policy_paragraphs").fetchone()[0],
        "requests": conn.execute("SELECT COUNT(*) FROM requests").fetchone()[0],
        "prior_decisions": conn.execute("SELECT COUNT(*) FROM prior_decisions").fetchone()[0],
    }
    conn.close()
    return {
        "loaded": counts,
        "policy_compiled": compiled,
        "compiler_summary": summary,
        "proposed_rules": srv.list_rules(status="proposed"),
        "next_step": "POST /api/rules/approve-all-verified (one click) or approve/reject rules individually, then POST /api/runs.",
    }


# ---------------------------------------------------------------------------
# Runs: start in the background, poll status/events/verdicts
# ---------------------------------------------------------------------------

_background_run_tasks: dict[str, asyncio.Task] = {}


async def _run_pipeline_in_background(request_ids: list[str], benchmark_mode: bool, run_id: str) -> None:
    try:
        await chair.run_full_pipeline(request_ids, benchmark_mode=benchmark_mode, run_id=run_id)
    except Exception as exc:  # pragma: no cover -- chair.run_full_pipeline already catches RunLimitHit itself
        conn = get_connection()
        conn.execute(
            "UPDATE runs SET status = 'failed', finished_at = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), run_id),
        )
        conn.commit()
        audit.log_event(conn, run_id, "run_failed_unexpected", {"error": repr(exc)})
        conn.close()


class StartRunRequest(BaseModel):
    request_ids: Optional[list[str]] = None
    benchmark_mode: bool = False


@app.post("/api/runs")
async def start_run(body: StartRunRequest = StartRunRequest()) -> dict:
    # Must be `async def`: a sync route runs in a worker thread with no running event loop, so
    # asyncio.create_task there raises "no current event loop in thread". `async def` runs
    # directly on the main loop, which is what lets the background task keep running on it after
    # this request returns.
    conn = get_connection()
    if body.request_ids:
        missing = [rid for rid in body.request_ids if not conn.execute("SELECT 1 FROM requests WHERE id = ?", (rid,)).fetchone()]
        if missing:
            conn.close()
            raise HTTPException(400, f"No such request id(s): {', '.join(missing)}.")
        request_ids = body.request_ids
    else:
        request_ids = [r["id"] for r in conn.execute("SELECT id FROM requests ORDER BY rowid")]
    conn.close()

    if not request_ids:
        raise HTTPException(400, "No requests loaded yet. POST /api/requests or POST /api/demo/load first.")

    run_id = f"run-{uuid.uuid4().hex[:8]}"
    task = asyncio.create_task(_run_pipeline_in_background(request_ids, body.benchmark_mode, run_id))
    _background_run_tasks[run_id] = task
    return {"run_id": run_id, "status": "started", "request_count": len(request_ids)}


@app.get("/api/runs/{run_id}")
def get_run(run_id: str) -> dict:
    conn = get_connection()
    row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(404, f"No run with id {run_id!r}.")
    run = dict(row)
    usage_rows = [dict(r) for r in conn.execute("SELECT * FROM usage WHERE run_id = ?", (run_id,))]
    conn.close()

    by_agent: dict[str, list] = {}
    for r in usage_rows:
        by_agent.setdefault(_agent_family(r["agent"]), []).append(r)
    run["progress_by_agent"] = {name: {"calls": len(rows)} for name, rows in by_agent.items()}
    run["usage_total"] = _usage_totals(usage_rows)
    return run


@app.get("/api/runs/{run_id}/events")
def get_run_events(run_id: str, limit: int = 500) -> list[dict]:
    """Ordered agent steps and tool calls for this run (the append-only audit trail). Polling is
    fine -- call this again for the latest events while a run is still in progress."""
    conn = get_connection()
    run_exists = conn.execute("SELECT 1 FROM runs WHERE id = ?", (run_id,)).fetchone()
    if not run_exists:
        conn.close()
        raise HTTPException(404, f"No run with id {run_id!r}.")
    rows = [dict(r) for r in conn.execute("SELECT * FROM audit WHERE run_id = ? ORDER BY id LIMIT ?", (run_id, limit))]
    conn.close()
    return rows


@app.get("/api/runs/{run_id}/verdicts")
def get_run_verdicts(run_id: str) -> list[dict]:
    conn = get_connection()
    run_exists = conn.execute("SELECT 1 FROM runs WHERE id = ?", (run_id,)).fetchone()
    if not run_exists:
        conn.close()
        raise HTTPException(404, f"No run with id {run_id!r}.")
    rows = [
        dict(r)
        for r in conn.execute(
            """SELECT v.*, l.description, l.amount, l.request_id, req.club
               FROM verdicts v JOIN lines l ON l.id = v.line_id JOIN requests req ON req.id = l.request_id
               WHERE v.run_id = ? ORDER BY l.rowid""",
            (run_id,),
        )
    ]
    conn.close()
    return rows


@app.get("/api/runs/{run_id}/drafts")
def get_run_drafts(run_id: str) -> list[dict]:
    conn = get_connection()
    run_exists = conn.execute("SELECT 1 FROM runs WHERE id = ?", (run_id,)).fetchone()
    if not run_exists:
        conn.close()
        raise HTTPException(404, f"No run with id {run_id!r}.")
    rows = [dict(r) for r in conn.execute("SELECT * FROM drafts WHERE run_id = ? ORDER BY created_at", (run_id,))]
    conn.close()
    for row in rows:
        row["content"] = json.loads(row.pop("content_json"))
    return rows


class ApproveDraftRequest(BaseModel):
    by: str


@app.post("/api/drafts/{draft_id}/approve")
def approve_draft_route(draft_id: str, body: ApproveDraftRequest) -> dict:
    """The committee-approval gate: nothing a Drafter wrote is final until this is called."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM drafts WHERE id = ?", (draft_id,)).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(404, f"No draft with id {draft_id!r}.")
    conn.execute("UPDATE drafts SET status = 'approved' WHERE id = ?", (draft_id,))
    conn.commit()
    audit.log_event(conn, row["run_id"], "draft_approved", {"draft_id": draft_id, "approved_by": body.by})
    conn.close()
    return {"draft_id": draft_id, "approved": True, "approved_by": body.by}


# ---------------------------------------------------------------------------
# Consistency, optimizer, line explanation, export
# ---------------------------------------------------------------------------


@app.get("/api/consistency")
def consistency_route() -> dict:
    return srv.consistency_report()


class AllocateRequest(BaseModel):
    pot: float
    alpha: float


@app.post("/api/allocate")
def allocate_route(body: AllocateRequest) -> dict:
    """Instant, code only -- no model call."""
    if not (0.0 <= body.alpha <= 1.0):
        raise HTTPException(400, "alpha must be between 0 and 1.")
    if body.pot < 0:
        raise HTTPException(400, "pot must be non-negative.")
    return srv.allocate(body.pot, body.alpha)


@app.get("/api/lines/{line_id}/explain")
def explain_line_route(line_id: str) -> dict:
    conn = get_connection()
    row = conn.execute("SELECT request_id FROM lines WHERE id = ?", (line_id,)).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(404, f"No line with id {line_id!r}.")
    result = srv.explain_line(row["request_id"], line_id)
    if not result["found"]:
        raise HTTPException(404, f"Could not explain line {line_id!r} (no verdict computed for it yet -- run the pipeline first).")
    return result


@app.get("/api/export.csv")
def export_csv(run_id: str) -> Response:
    """The engine's verdicts for one run, as a CSV -- working data for the committee, not the
    draft memo (that's gated separately by POST /api/drafts/{id}/approve)."""
    conn = get_connection()
    run_exists = conn.execute("SELECT 1 FROM runs WHERE id = ?", (run_id,)).fetchone()
    if not run_exists:
        conn.close()
        raise HTTPException(404, f"No run with id {run_id!r}.")
    rows = conn.execute(
        """SELECT req.club, l.request_id, v.line_id, l.description, l.amount, v.verdict,
                  v.allowed_amount, v.rules_json, v.flagged_for_review
           FROM verdicts v JOIN lines l ON l.id = v.line_id JOIN requests req ON req.id = l.request_id
           WHERE v.run_id = ? ORDER BY req.club, l.rowid""",
        (run_id,),
    ).fetchall()
    conn.close()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["club", "request_id", "line_id", "description", "amount", "verdict", "allowed_amount", "rule_citations", "flagged_for_review"])
    for row in rows:
        writer.writerow([row[k] for k in ("club", "request_id", "line_id", "description", "amount", "verdict", "allowed_amount", "rules_json", "flagged_for_review")])
    return Response(
        content=buf.getvalue(), media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=gavel_verdicts_{run_id}.csv"},
    )


if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
else:

    @app.get("/", response_class=HTMLResponse)
    def placeholder() -> str:
        return PLACEHOLDER_HTML
