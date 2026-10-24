"""Exercises every route in backend/main.py with the real FastAPI app (TestClient), against a
real database -- no mocks. A few routes make real model calls (POST /api/policy/compile,
/api/demo/load); POST /api/runs is tested against a small 2-request subset to keep the real
background pipeline run fast and cheap rather than the full 24.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from backend.load import main as reload_fresh_db
from backend.main import app

SAMPLE_POLICY_TEXT = """SAMPLE POLICY (TEST FIXTURE)

9.1  Funds may not be used to purchase alcohol.
9.2  Club apparel is funded up to $20 per item.
"""

# A bare `TestClient(app)` (no `with`) never opens its anyio "portal", so every call gets its own
# ad hoc event loop -- fine for routes with no state across calls, but the Policy Compiler agent's
# MCPToolset keeps a stdio session tied to whichever loop first created it, so a second route call
# on a NEW loop crashes with "Event loop is closed". A single `with TestClient(app) as client:`
# opens one persistent portal (one event loop) for the whole module, matching how every other real
# run in this repo (run_check.py, benchmark.py, safety_test.py) stays on one asyncio.run() loop.
_client_cm = TestClient(app)
client = _client_cm.__enter__()


@pytest.fixture(scope="module", autouse=True)
def fresh_db():
    reload_fresh_db()
    yield
    _client_cm.__exit__(None, None, None)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Policy: upload/paste, compile, approve/reject
# ---------------------------------------------------------------------------


def test_upload_policy_requires_file_or_text():
    response = client.post("/api/policy")
    assert response.status_code == 400
    assert "file" in response.json()["detail"].lower()


def test_upload_policy_rejects_unparseable_text():
    response = client.post("/api/policy", data={"text": "no paragraphs here, just prose"})
    assert response.status_code == 400
    assert "no policy paragraphs" in response.json()["detail"].lower()


def test_upload_policy_paste_text():
    response = client.post("/api/policy", data={"text": SAMPLE_POLICY_TEXT})
    assert response.status_code == 200
    assert response.json()["paragraphs_loaded"] == 2


def test_compile_policy_real_call():
    response = client.post("/api/policy/compile")
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["paragraphs_reviewed"] == 2
    assert len(body["rules"]) >= 1
    assert all(r["status"] == "proposed" for r in body["rules"])


def test_approve_rule_requires_verified_quote():
    response = client.post("/api/rules/NO-SUCH-RULE/approve", json={"by": "test-chair"})
    assert response.status_code == 400


def test_approve_and_reject_rules():
    compile_response = client.post("/api/policy/compile")
    proposed = [r for r in compile_response.json()["rules"] if r["status"] == "proposed"]
    assert len(proposed) >= 2

    approve_response = client.post(f"/api/rules/{proposed[0]['id']}/approve", json={"by": "test-chair"})
    assert approve_response.status_code == 200
    assert approve_response.json()["approved"] is True

    reject_response = client.post(f"/api/rules/{proposed[1]['id']}/reject", json={"by": "test-chair", "reason": "test"})
    assert reject_response.status_code == 200
    assert reject_response.json()["rejected"] is True

    reject_missing = client.post("/api/rules/NO-SUCH-RULE/reject", json={"by": "test-chair"})
    assert reject_missing.status_code == 404


def test_approve_all_verified():
    client.post("/api/policy", data={"text": SAMPLE_POLICY_TEXT})
    client.post("/api/policy/compile")
    response = client.post("/api/rules/approve-all-verified", json={"by": "test-chair"})
    assert response.status_code == 200
    assert response.json()["count"] >= 1


# ---------------------------------------------------------------------------
# Requests: paste JSON, upload txt/html/json
# ---------------------------------------------------------------------------


def test_create_request_via_json_paste():
    payload = {
        "club": "Test Club", "event_date": "2026-12-01", "submitted_date": "2026-11-01",
        "justification": "A test event.",
        "lines": [{"description": "Venue rental", "amount": 300, "docs": [], "already_purchased": False}],
    }
    response = client.post("/api/requests", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["lines_loaded"] == 1
    assert body["request_id"]


def test_create_request_via_json_paste_rejects_missing_fields():
    response = client.post("/api/requests", json={"club": "Test Club"})
    assert response.status_code == 400
    assert "missing" in response.json()["detail"].lower()


def test_create_request_via_txt_upload():
    text = (
        "Club: Text Upload Club\n"
        "Event: 2026-12-05\n"
        "Submitted: 2026-11-01\n"
        "Justification: Our annual showcase.\n"
        "Lines:\n"
        "- Venue rental - $250\n"
        "- Hotel block - $1200 [docs: quotes3]\n"
    )
    response = client.post("/api/requests", files={"file": ("request.txt", text, "text/plain")})
    assert response.status_code == 200
    assert response.json()["lines_loaded"] == 2


def test_create_request_via_txt_upload_bad_format():
    response = client.post("/api/requests", files={"file": ("bad.txt", "not a valid request", "text/plain")})
    assert response.status_code == 400
    assert "expected plain-text format" in response.json()["detail"].lower()


def test_create_request_via_json_upload():
    import json

    payload = {
        "club": "JSON Upload Club", "event_date": "2026-12-10", "submitted_date": "2026-11-05",
        "justification": "A test event via file upload.",
        "lines": [{"description": "Printing", "amount": 100, "docs": [], "already_purchased": False}],
    }
    response = client.post("/api/requests", files={"file": ("request.json", json.dumps(payload), "application/json")})
    assert response.status_code == 200
    assert response.json()["lines_loaded"] == 1


def test_create_request_via_html_upload():
    html = (
        '<!doctype html><html><head><title>Request UPHTML</title></head><body>'
        '<h3>Funding request UPHTML: HTML Upload Club</h3>'
        '<p>Event: 2026-12-15 Submitted: 2026-11-10</p>'
        '<p>Our club plans a showcase event.</p>'
        '<p>L1: Printing of posters - $150<br>L2: Venue rental - $200</p></body></html>'
    )
    response = client.post("/api/requests", files={"file": ("request.html", html, "text/html")})
    assert response.status_code == 200
    assert response.json()["lines_loaded"] == 2


def test_create_request_rejects_bad_content_type():
    response = client.post(
        "/api/requests", content=b"plain text, no content-type match", headers={"content-type": "text/plain"}
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Demo load
# ---------------------------------------------------------------------------


def test_demo_load_real_call():
    response = client.post("/api/demo/load")
    assert response.status_code == 200
    body = response.json()
    assert body["loaded"]["policy_paragraphs"] == 16
    assert body["loaded"]["requests"] == 27  # 24 real + 2 safety JSON + 1 HTML
    assert body["loaded"]["prior_decisions"] == 30
    assert body["policy_compiled"] is True
    assert len(body["proposed_rules"]) >= 1


# ---------------------------------------------------------------------------
# Runs: start in background on a small subset, poll to completion
# ---------------------------------------------------------------------------


def test_start_and_poll_run():
    approve_response = client.post("/api/rules/approve-all-verified", json={"by": "test-chair"})
    assert approve_response.status_code == 200

    start_response = client.post("/api/runs", json={"request_ids": ["Q01", "Q02"], "benchmark_mode": True})
    assert start_response.status_code == 200
    run_id = start_response.json()["run_id"]
    assert start_response.json()["request_count"] == 2

    deadline = time.monotonic() + 60
    status = None
    while time.monotonic() < deadline:
        status_response = client.get(f"/api/runs/{run_id}")
        assert status_response.status_code == 200
        status = status_response.json()["status"]
        if status != "running":
            break
        time.sleep(1)
    assert status == "completed", f"run did not complete in time, last status: {status}"

    events_response = client.get(f"/api/runs/{run_id}/events")
    assert events_response.status_code == 200
    assert len(events_response.json()) > 0

    verdicts_response = client.get(f"/api/runs/{run_id}/verdicts")
    assert verdicts_response.status_code == 200
    verdicts = verdicts_response.json()
    assert len(verdicts) > 0
    assert all("club" in v and "description" in v for v in verdicts)

    drafts_response = client.get(f"/api/runs/{run_id}/drafts")
    assert drafts_response.status_code == 200
    assert all(d["status"] == "awaiting_approval" for d in drafts_response.json())

    if drafts_response.json():
        draft_id = drafts_response.json()[0]["id"]
        approve_draft_response = client.post(f"/api/drafts/{draft_id}/approve", json={"by": "test-chair"})
        assert approve_draft_response.status_code == 200
        assert approve_draft_response.json()["approved"] is True

    export_response = client.get(f"/api/export.csv?run_id={run_id}")
    assert export_response.status_code == 200
    assert export_response.headers["content-type"].startswith("text/csv")
    assert "club,request_id,line_id" in export_response.text

    explain_response = client.get("/api/lines/01-L1/explain")
    assert explain_response.status_code == 200
    assert "citations" in explain_response.json()


def test_get_run_not_found():
    assert client.get("/api/runs/NO-SUCH-RUN").status_code == 404
    assert client.get("/api/runs/NO-SUCH-RUN/events").status_code == 404
    assert client.get("/api/runs/NO-SUCH-RUN/verdicts").status_code == 404
    assert client.get("/api/runs/NO-SUCH-RUN/drafts").status_code == 404


def test_start_run_with_unknown_request_id():
    response = client.post("/api/runs", json={"request_ids": ["Q99-no-such"]})
    assert response.status_code == 400


def test_explain_line_not_found():
    response = client.get("/api/lines/NO-SUCH-LINE/explain")
    assert response.status_code == 404


def test_approve_draft_not_found():
    response = client.post("/api/drafts/NO-SUCH-DRAFT/approve", json={"by": "test-chair"})
    assert response.status_code == 404


def test_export_csv_not_found():
    response = client.get("/api/export.csv?run_id=NO-SUCH-RUN")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Consistency, optimizer, usage
# ---------------------------------------------------------------------------


def test_consistency_route():
    response = client.get("/api/consistency")
    assert response.status_code == 200
    body = response.json()
    assert "inconsistent_count" in body


def test_allocate_route():
    response = client.post("/api/allocate", json={"pot": 40000, "alpha": 0.5})
    assert response.status_code == 200
    assert "allocation" in response.json()


def test_allocate_rejects_bad_alpha():
    response = client.post("/api/allocate", json={"pot": 40000, "alpha": 1.5})
    assert response.status_code == 400


def test_allocate_rejects_negative_pot():
    response = client.post("/api/allocate", json={"pot": -1, "alpha": 0.5})
    assert response.status_code == 400


def test_usage_and_runs_routes_still_work():
    assert client.get("/api/usage").status_code == 200
    assert client.get("/api/runs").status_code == 200
