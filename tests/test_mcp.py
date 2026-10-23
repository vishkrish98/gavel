"""Exercises every MCP tool in mcp_server/server.py against real data (the actual synthetic
policy/requests loaded by backend/load.py, plus the real answer-key facts from
data/requests_truth.json used here only as a test fixture -- never read by an agent). No model
calls anywhere in this file; every tool under test is deterministic.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import mcp_server.server as srv
from backend.db import get_connection
from backend.load import main as reload_fresh_db

DATA = ROOT / "data"


@pytest.fixture(scope="module", autouse=True)
def fresh_loaded_db():
    """Reload the database fresh once for this whole test module."""
    reload_fresh_db()
    yield


@pytest.fixture(scope="module")
def approved_truth_rules():
    """Propose + approve the 12 true rules via the real propose_rule/approve_rule tools (not a
    DB shortcut) -- this doubles as the test for that approval flow."""
    truth = json.loads((DATA / "policy_rules_truth.json").read_text())
    rule_ids = {}
    for r in truth["rules"]:
        params = {k: v for k, v in r.items() if k not in ("rule_id", "para", "type", "quote")}
        proposed = srv.propose_rule(r["para"], r["type"], params, r["quote"])
        assert proposed["status"] == "proposed", f"expected {r['rule_id']} to verify, got {proposed}"
        approved = srv.approve_rule(proposed["rule_id"], "test-committee-chair")
        assert approved["approved"] is True
        rule_ids[r["rule_id"]] = proposed["rule_id"]
    return rule_ids


@pytest.fixture(scope="module")
def classified_lines():
    """Write the TRUE line facts (category, headcount, qty, nights, unit_cost) from
    data/requests_truth.json directly into the lines table -- standing in for the Request Reader
    agent, which doesn't exist until step04. Labeled here as a test fixture, same as step03 does."""
    truth = json.loads((DATA / "requests_truth.json").read_text())["requests"]
    conn = get_connection()
    for request_id, info in truth.items():
        for line_id, facts in info["lines"].items():
            conn.execute(
                "UPDATE lines SET category=?, headcount=?, qty=?, nights=?, unit_cost=? WHERE id=?",
                (facts["category"], facts["headcount"], facts["qty"], facts["nights"], facts["unit_cost"], line_id),
            )
    conn.commit()
    conn.close()
    return truth


# ---------------------------------------------------------------------------
# Policy and rules
# ---------------------------------------------------------------------------


def test_load_policy_returns_16_paragraphs_unclassified():
    paragraphs = srv.load_policy()
    assert len(paragraphs) == 16
    assert all(p["kind"] is None for p in paragraphs)


def test_verify_quote_exact_match_true():
    result = srv.verify_quote("3.1", "Funds may not be used to purchase alcohol.")
    assert result["verified"] is True


def test_verify_quote_fake_quote_rejected():
    result = srv.verify_quote("3.1", "Funds may not be used to purchase unicorns.")
    assert result["verified"] is False


def test_verify_quote_normalizes_whitespace_never_fuzzy():
    # Extra internal whitespace still matches (normalized)...
    assert srv.verify_quote("3.8", "Club   apparel is  funded up to $20 per item.")["verified"] is True
    # ...but a real semantic paraphrase (not a literal substring) must NOT match -- no fuzzy match.
    assert srv.verify_quote("3.8", "Club apparel is funded up to twenty dollars per item.")["verified"] is False


def test_propose_rule_with_real_quote_is_proposed_not_approved():
    result = srv.propose_rule(
        "3.2", "prohibited_category", {"category": "gift_card"}, "Funds may not be used to purchase gift cards."
    )
    assert result["status"] == "proposed"
    assert result["quote_verified"] is True
    rules = srv.list_rules(status="proposed")
    assert any(r["id"] == result["rule_id"] for r in rules)


def test_propose_rule_with_fake_quote_is_rejected_with_audit_entry():
    result = srv.propose_rule(
        "3.2", "prohibited_category", {"category": "tobacco"}, "Funds may not be used to purchase tobacco."
    )
    assert result["status"] == "rejected"
    assert result["quote_verified"] is False

    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM audit WHERE event = 'rule_rejected' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    assert row is not None
    detail = json.loads(row["detail_json"])
    assert detail["rule_id"] == result["rule_id"]
    assert detail["reason"] == "quote_not_found"


def test_approve_rule_refuses_unverified_quote():
    rejected = srv.propose_rule("3.1", "prohibited_category", {"category": "nothing"}, "not a real quote")
    result = srv.approve_rule(rejected["rule_id"], "test-chair")
    assert result["approved"] is False


def test_approve_rule_marks_approved_by(approved_truth_rules):
    rules = srv.list_rules(status="approved")
    assert len(rules) == 12
    assert all(r["approved_by"] == "test-committee-chair" for r in rules)


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


def test_get_request_returns_all_lines():
    result = srv.get_request("Q01")
    assert result["found"] is True
    assert result["club"] == "Robotics Club"
    assert len(result["lines"]) == 8


def test_get_request_not_found():
    assert srv.get_request("Q99")["found"] is False


# ---------------------------------------------------------------------------
# Engine: check_line / run_engine / explain_line against the real answer key
# ---------------------------------------------------------------------------


def test_run_engine_matches_truth_for_one_request(approved_truth_rules, classified_lines):
    truth = classified_lines["Q01"]["lines"]
    result = srv.run_engine("Q01")
    for line_id, expected in truth.items():
        actual = result["lines"][line_id]
        assert actual["verdict"] == expected["verdict"], f"{line_id}: {actual} != {expected}"
        assert actual["allowed_amount"] == expected["allowed_amount"], f"{line_id}: {actual} != {expected}"
        # approve_rule generated fresh rule ids (RULE-xxxx), not the truth file's R01..R12 --
        # translate through the fixture's mapping before comparing which rules fired.
        expected_ids = sorted(approved_truth_rules[r] for r in expected["rules"])
        assert sorted(actual["rules"]) == expected_ids, f"{line_id}: {actual} != {expected}"


def test_run_engine_matches_truth_for_every_real_request(approved_truth_rules, classified_lines):
    conn = get_connection()
    request_ids = [r["id"] for r in conn.execute("SELECT id FROM requests WHERE source = 'requests_input.json'")]
    conn.close()
    total = 0
    mismatches = []
    for request_id in request_ids:
        truth_lines = classified_lines[request_id]["lines"]
        result = srv.run_engine(request_id)["lines"]
        for line_id, expected in truth_lines.items():
            total += 1
            actual = result[line_id]
            if actual["verdict"] != expected["verdict"] or actual["allowed_amount"] != expected["allowed_amount"]:
                mismatches.append((line_id, actual, expected))
    assert total == 158, f"expected 158 real lines, saw {total}"
    assert mismatches == [], f"{len(mismatches)} mismatches: {mismatches[:5]}"


def test_check_line_matches_run_engine(approved_truth_rules, classified_lines):
    via_check = srv.check_line("Q01", "01-L2")
    via_run = srv.run_engine("Q01")["lines"]["01-L2"]
    assert via_check["verdict"] == via_run["verdict"]
    assert via_check["allowed_amount"] == via_run["allowed_amount"]
    assert via_check["rules"] == via_run["rules"]


def test_explain_line_returns_exact_policy_quote(approved_truth_rules, classified_lines):
    # 01-L2 (lodging, 3 rooms x 2 nights x $190, over $500, no quotes3 doc) hits R05 (requires_docs).
    result = srv.explain_line("Q01", "01-L2")
    assert result["verdict"] == "needs_docs"
    assert len(result["citations"]) == 1
    citation = result["citations"][0]
    assert citation["para_id"] == "3.5"
    assert citation["quote"] == "Any single purchase over $500 requires three written quotes."


# ---------------------------------------------------------------------------
# Consistency report
# ---------------------------------------------------------------------------


def test_consistency_report_matches_6_of_30(approved_truth_rules, classified_lines):
    report = srv.consistency_report()
    assert report["matched"] == 30, f"expected all 30 prior decisions to match a current line, got {report['matched']}"
    assert report["inconsistent_count"] == 6, report


# ---------------------------------------------------------------------------
# Optimizer
# ---------------------------------------------------------------------------


def test_allocate_caps_each_club_at_its_allowed_amount(approved_truth_rules, classified_lines):
    club_history = json.loads((DATA / "club_history.json").read_text())
    pot = club_history["pot"]
    result = srv.allocate(pot, 0.5)
    for club, amount in result["allocation"].items():
        assert amount <= result["allowed_by_club"][club] + 1e-6
    # The pot ($40,000) is far below total allowed ($57,273 per CONTEXT.md), so the whole pot
    # should be spent, not left on the table.
    assert sum(result["allocation"].values()) == pytest.approx(pot, abs=1.0)


def test_allocate_pure_function_matches_optimizer_truth():
    from backend.engine import allocate as pure_allocate

    truth = json.loads((DATA / "optimizer_truth.json").read_text())
    util = {c["club"]: c["utilization"] for c in json.loads((DATA / "club_history.json").read_text())["clubs"]}
    for scenario_name, expected in truth["scenarios"].items():
        if scenario_name.startswith("alpha_"):
            alpha = float(scenario_name.split("_", 1)[1])
            pot = truth["pot"]
        else:
            pot_str, alpha_str = scenario_name.replace("pot_", "").split("_alpha_")
            pot, alpha = float(pot_str), float(alpha_str)
        actual = pure_allocate(truth["allowed_by_club"], util, pot, alpha)
        for club, expected_amount in expected.items():
            assert actual[club] == pytest.approx(expected_amount, abs=0.01), f"{scenario_name}/{club}"


# ---------------------------------------------------------------------------
# Usage logging
# ---------------------------------------------------------------------------


def test_log_usage_computes_cost_from_pricing_config():
    from backend.pricing import compute_cost_usd

    result = srv.log_usage(
        run_id="test-run-1", agent="test-agent",
        input_tokens=1000, cached_tokens=200, cache_write_tokens=0,
        output_tokens=500, reasoning_tokens=100, seconds=2.5,
    )
    expected_cost = compute_cost_usd(1000, 200, 0, 500)
    assert result["cost_usd"] == pytest.approx(expected_cost)
    assert result["total_tokens"] == 1500

    conn = get_connection()
    row = conn.execute("SELECT * FROM usage WHERE run_id = 'test-run-1'").fetchone()
    conn.close()
    assert row is not None
    assert row["model"] == "gpt-6-luna"
