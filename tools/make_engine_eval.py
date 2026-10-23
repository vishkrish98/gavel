"""Generates evidence/engine_eval.json: proves the deterministic engine (backend/engine.py,
mcp_server/server.py) reproduces tools/make_funding_data.py's reference answer key exactly, with
ZERO model calls. Run with: python -m tools.make_engine_eval

This is a validation step, not a new feature: it loads the 12 TRUE rules and TRUE line facts as
a labeled test fixture (standing in for the Policy Compiler and Request Reader agents, which
don't exist until step04), then checks the real run_engine/allocate/consistency_report tools
against the answer key.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import mcp_server.server as srv
from backend.db import get_connection
from backend.engine import allocate as pure_allocate
from backend.load import main as reload_fresh_db

DATA = ROOT / "data"
OUTPUT = ROOT / "evidence" / "engine_eval.json"


def load_fixture_rules() -> dict[str, str]:
    """Propose + approve the 12 true rules through the real propose_rule/approve_rule tools.
    Returns a map from the truth file's rule_id (R01..R12) to the freshly generated rule id."""
    truth = json.loads((DATA / "policy_rules_truth.json").read_text())
    rule_id_map = {}
    for r in truth["rules"]:
        params = {k: v for k, v in r.items() if k not in ("rule_id", "para", "type", "quote")}
        proposed = srv.propose_rule(r["para"], r["type"], params, r["quote"])
        assert proposed["status"] == "proposed", f"rule {r['rule_id']} failed to verify: {proposed}"
        approved = srv.approve_rule(proposed["rule_id"], "step03-fixture")
        assert approved["approved"], approved
        rule_id_map[r["rule_id"]] = proposed["rule_id"]
    return rule_id_map


def load_fixture_line_facts() -> dict:
    """Write the TRUE per-line facts directly into the lines table -- the Request Reader's job,
    not built until step04. Returns the parsed truth data for comparison."""
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


def check_engine_against_truth(truth: dict, rule_id_map: dict[str, str]) -> dict:
    conn = get_connection()
    real_request_ids = [r["id"] for r in conn.execute("SELECT id FROM requests WHERE source = 'requests_input.json'")]
    conn.close()

    total = 0
    verdict_matches = 0
    amount_matches = 0
    rules_matches = 0
    mismatches = []
    for request_id in real_request_ids:
        truth_lines = truth[request_id]["lines"]
        engine_lines = srv.run_engine(request_id)["lines"]
        for line_id, expected in truth_lines.items():
            total += 1
            actual = engine_lines[line_id]
            expected_rule_ids = sorted(rule_id_map[r] for r in expected["rules"])
            actual_rule_ids = sorted(actual["rules"])
            v_ok = actual["verdict"] == expected["verdict"]
            a_ok = actual["allowed_amount"] == expected["allowed_amount"]
            r_ok = actual_rule_ids == expected_rule_ids
            verdict_matches += v_ok
            amount_matches += a_ok
            rules_matches += r_ok
            if not (v_ok and a_ok and r_ok):
                mismatches.append(
                    {
                        "request_id": request_id, "line_id": line_id,
                        "expected": expected, "actual": actual, "actual_rule_ids_translated": actual_rule_ids,
                    }
                )
    return {
        "total_lines": total,
        "verdict_matches": verdict_matches,
        "amount_matches": amount_matches,
        "rules_matches": rules_matches,
        "both_verdict_and_amount_match": total - len({(m["request_id"], m["line_id"]) for m in mismatches}),
        "mismatches": mismatches,
    }


def check_allocate_against_truth() -> dict:
    optimizer_truth = json.loads((DATA / "optimizer_truth.json").read_text())
    club_history = json.loads((DATA / "club_history.json").read_text())
    util = {c["club"]: c["utilization"] for c in club_history["clubs"]}
    allowed = optimizer_truth["allowed_by_club"]

    scenario_results = {}
    all_exact = True
    for scenario_name, expected_alloc in optimizer_truth["scenarios"].items():
        if scenario_name.startswith("alpha_"):
            alpha = float(scenario_name.split("_", 1)[1])
            pot = optimizer_truth["pot"]
        else:
            pot_str, alpha_str = scenario_name.replace("pot_", "").split("_alpha_")
            pot, alpha = float(pot_str), float(alpha_str)
        actual_alloc = pure_allocate(allowed, util, pot, alpha)
        diffs = {
            club: round(actual_alloc[club] - expected_alloc[club], 6)
            for club in expected_alloc
            if round(actual_alloc[club] - expected_alloc[club], 2) != 0
        }
        exact = not diffs
        all_exact = all_exact and exact
        scenario_results[scenario_name] = {
            "pot": pot, "alpha": alpha, "exact_match_to_the_cent": exact,
            "diffs_over_a_cent": diffs,
        }
    return {"scenarios": scenario_results, "all_four_exact_to_the_cent": all_exact}


def main() -> None:
    reload_fresh_db()
    rule_id_map = load_fixture_rules()
    truth = load_fixture_line_facts()

    engine_check = check_engine_against_truth(truth, rule_id_map)
    allocate_check = check_allocate_against_truth()
    consistency = srv.consistency_report()

    result = {
        "note": (
            "Validates the deterministic engine (backend/engine.py, mcp_server/server.py) against "
            "the reference answer key computed by tools/make_funding_data.py. Zero model calls: "
            "the 12 rules and all line facts are loaded as a labeled test fixture standing in for "
            "the Policy Compiler and Request Reader agents (step04), not produced by a model here."
        ),
        "tokens_used": 0,
        "tokens_used_note": "Zero. This entire step is the deterministic engine only -- no agent, no model call, anywhere in this evaluation.",
        "engine_vs_truth": engine_check,
        "allocate_vs_optimizer_truth": allocate_check,
        "consistency_report": consistency,
        "expectations": {
            "158_of_158_lines_match_verdict_and_amount": engine_check["total_lines"] == 158
            and engine_check["both_verdict_and_amount_match"] == 158,
            "allocate_exact_to_the_cent_all_4_scenarios": allocate_check["all_four_exact_to_the_cent"],
            "consistency_6_of_30_inconsistent": consistency["matched"] == 30 and consistency["inconsistent_count"] == 6,
        },
    }
    OUTPUT.write_text(json.dumps(result, indent=2, default=str))

    print(f"lines: {engine_check['total_lines']}, both verdict+amount match: {engine_check['both_verdict_and_amount_match']}")
    print(f"allocate all 4 scenarios exact to the cent: {allocate_check['all_four_exact_to_the_cent']}")
    print(f"consistency: {consistency['inconsistent_count']} of {consistency['matched']} inconsistent")
    print(f"tokens used: 0 (deterministic engine only, no model calls)")
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
