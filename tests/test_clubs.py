"""Exercises the post-11b clubs registry and bulk-import routes against the real FastAPI app and
a real database -- no mocks. No model calls here (policy compile/agent runs are already covered by
tests/test_api.py); this focuses on the import/validation/balance-computation logic itself.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from fastapi.testclient import TestClient

from backend.load import main as reload_fresh_db
from backend.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def fresh_db():
    reload_fresh_db()
    yield


def test_demo_data_seeds_24_clubs_with_real_budgets():
    response = client.get("/api/clubs")
    assert response.status_code == 200
    clubs = response.json()
    assert len(clubs) == 24
    robotics = next(c for c in clubs if c["name"] == "Robotics Club")
    assert robotics["pre_approved_budget"] == 6000
    assert robotics["remaining_balance"] == 6000  # no requests reviewed yet
    assert robotics["spent"] == 0
    assert robotics["lines_reviewed"] == 0


def test_bulk_club_import_validates_and_imports():
    response = client.post(
        "/api/clubs/bulk",
        json=[
            {"name": "New Robotics Offshoot", "category": "academic", "pre_approved_budget": 3000},
            {"name": "Underwater Basket Weaving", "pre_approved_budget": 500},
        ],
    )
    assert response.status_code == 200
    result = response.json()
    assert result["imported"] == 2

    clubs = {c["name"]: c for c in client.get("/api/clubs").json()}
    assert clubs["New Robotics Offshoot"]["pre_approved_budget"] == 3000
    assert clubs["New Robotics Offshoot"]["category"] == "academic"
    assert clubs["Underwater Basket Weaving"]["pre_approved_budget"] == 500
    assert clubs["Underwater Basket Weaving"]["category"] is None


def test_bulk_club_import_rejects_missing_name():
    response = client.post("/api/clubs/bulk", json=[{"pre_approved_budget": 1000}])
    assert response.status_code == 400
    assert "name" in response.json()["detail"]


def test_bulk_club_import_rejects_empty_list():
    response = client.post("/api/clubs/bulk", json=[])
    assert response.status_code == 400


def test_reimporting_a_club_by_name_updates_its_budget():
    client.post("/api/clubs/bulk", json=[{"name": "Robotics Club", "pre_approved_budget": 9999}])
    clubs = {c["name"]: c for c in client.get("/api/clubs").json()}
    assert len(client.get("/api/clubs").json()) == 24, "re-importing an existing name must update, not duplicate"
    assert clubs["Robotics Club"]["pre_approved_budget"] == 9999


def test_bulk_request_import_partial_success():
    response = client.post(
        "/api/requests/bulk",
        json=[
            {
                "club": "Robotics Club",
                "event_date": "2026-12-01",
                "submitted_date": "2026-11-01",
                "justification": "test",
                "lines": [{"description": "Venue rental", "amount": 200}],
            },
            {"club": "Incomplete Club"},
        ],
    )
    assert response.status_code == 200
    result = response.json()
    assert result["total"] == 2
    assert result["succeeded"] == 1
    assert result["failed"] == 1
    assert result["results"][0]["status"] == "ok"
    assert result["results"][1]["status"] == "error"


def test_bulk_request_import_rejects_non_list_body():
    response = client.post(
        "/api/requests/bulk",
        json={"club": "Robotics Club", "event_date": "x", "submitted_date": "x", "justification": "x", "lines": []},
    )
    assert response.status_code == 400


def test_club_balance_reflects_real_verdicts():
    """Load one request for an existing club, insert a verdict directly as a labeled test fixture
    (the same pattern step02/step03's tests use to isolate one layer -- verdicts normally only come
    from a full chair.py pipeline run, which needs a real model call), and confirm the club's
    running balance drops by exactly the allowed amount."""
    from backend.db import get_connection

    bulk_response = client.post(
        "/api/requests/bulk",
        json=[
            {
                "club": "Robotics Club",
                "event_date": "2026-12-01",
                "submitted_date": "2026-11-01",
                "justification": "test",
                "lines": [{"description": "Office supplies", "amount": 123.45}],
            }
        ],
    )
    request_id = bulk_response.json()["results"][0]["request_id"]
    line_id = f"{request_id}-L1"

    run_id = "test-club-balance-run"
    conn = get_connection()
    conn.execute(
        "INSERT INTO verdicts (run_id, line_id, verdict, allowed_amount, rules_json) VALUES (?, ?, ?, ?, ?)",
        (run_id, line_id, "allowed", 123.45, "[]"),
    )
    conn.commit()
    conn.close()

    before = client.get("/api/clubs").json()
    robotics_before = next(c for c in before if c["name"] == "Robotics Club")
    assert robotics_before["spent"] == 123.45, "with no run_id given, the most recent run touching the club should be used"

    clubs_for_run = client.get(f"/api/clubs?run_id={run_id}").json()
    robotics = next(c for c in clubs_for_run if c["name"] == "Robotics Club")
    assert robotics["lines_reviewed"] == 1
    assert robotics["spent"] == 123.45
    assert robotics["remaining_balance"] == round(6000 - 123.45, 2)
