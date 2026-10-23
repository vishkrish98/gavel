"""Generates output/mcp_smoke.json: calls every MCP tool directly (in-process, the same way
tests/test_mcp.py does -- NOT over the stdio transport) against the real loaded database, and
records the real results. Run with: python -m tools.make_mcp_smoke
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
from backend.load import main as reload_fresh_db

DATA = ROOT / "data"
OUTPUT = ROOT / "output" / "mcp_smoke.json"


def main() -> None:
    reload_fresh_db()
    calls = []

    def record(name: str, args: dict, result):
        calls.append({"tool": name, "args": args, "result": result})

    # --- Policy / rules ---
    policy = srv.load_policy()
    record("load_policy", {}, {"count": len(policy), "sample": policy[:2]})

    real_quote = "Funds may not be used to purchase alcohol."
    verified = srv.verify_quote("3.1", real_quote)
    record("verify_quote", {"text_id": "3.1", "quote": real_quote}, verified)

    fake_quote = "Funds may not be used to purchase unicorns."
    rejected_quote = srv.verify_quote("3.1", fake_quote)
    record("verify_quote", {"text_id": "3.1", "quote": fake_quote}, rejected_quote)

    good_proposal = srv.propose_rule("3.1", "prohibited_category", {"category": "alcohol"}, real_quote)
    record(
        "propose_rule",
        {"para_id": "3.1", "type": "prohibited_category", "params": {"category": "alcohol"}, "quote": real_quote},
        good_proposal,
    )

    bad_proposal = srv.propose_rule("3.1", "prohibited_category", {"category": "tobacco"}, fake_quote)
    record(
        "propose_rule",
        {"para_id": "3.1", "type": "prohibited_category", "params": {"category": "tobacco"}, "quote": fake_quote},
        bad_proposal,
    )

    approval = srv.approve_rule(good_proposal["rule_id"], "demo-committee-chair")
    record("approve_rule", {"rule_id": good_proposal["rule_id"], "by": "demo-committee-chair"}, approval)

    approved_rules_list = srv.list_rules(status="approved")
    record("list_rules", {"status": "approved"}, approved_rules_list)
    rejected_rules_list = srv.list_rules(status="rejected")
    record("list_rules", {"status": "rejected"}, rejected_rules_list)

    # --- Propose + approve the full 12 true rules so the engine calls below are meaningful ---
    truth_rules = json.loads((DATA / "policy_rules_truth.json").read_text())["rules"]
    for r in truth_rules:
        if r["rule_id"] == "R01":
            continue  # already proposed/approved above as the "real quote" example
        params = {k: v for k, v in r.items() if k not in ("rule_id", "para", "type", "quote")}
        proposed = srv.propose_rule(r["para"], r["type"], params, r["quote"])
        srv.approve_rule(proposed["rule_id"], "demo-committee-chair")

    # --- Load the TRUE line facts as a test fixture (stands in for the step04 Request Reader) ---
    truth_requests = json.loads((DATA / "requests_truth.json").read_text())["requests"]
    conn = get_connection()
    for request_id, info in truth_requests.items():
        for line_id, facts in info["lines"].items():
            conn.execute(
                "UPDATE lines SET category=?, headcount=?, qty=?, nights=?, unit_cost=? WHERE id=?",
                (facts["category"], facts["headcount"], facts["qty"], facts["nights"], facts["unit_cost"], line_id),
            )
    conn.commit()
    conn.close()

    # --- Requests / engine ---
    request = srv.get_request("Q01")
    record("get_request", {"request_id": "Q01"}, request)

    check = srv.check_line("Q01", "01-L2")
    record("check_line", {"request_id": "Q01", "line_id": "01-L2"}, check)

    engine_result = srv.run_engine("Q01")
    record("run_engine", {"request_id": "Q01"}, engine_result)

    explanation = srv.explain_line("Q01", "01-L2")
    record("explain_line", {"request_id": "Q01", "line_id": "01-L2"}, explanation)

    # --- Consistency ---
    consistency = srv.consistency_report()
    record("consistency_report", {}, {**consistency, "decisions": consistency["decisions"][:3] + ["...(27 more)"]})

    # --- Optimizer ---
    club_history = json.loads((DATA / "club_history.json").read_text())
    allocation = srv.allocate(club_history["pot"], 0.5)
    record("allocate", {"pot": club_history["pot"], "alpha": 0.5}, allocation)

    # --- Token usage logging ---
    usage = srv.log_usage(
        run_id="smoke-run-1", agent="demo-agent",
        input_tokens=1200, cached_tokens=300, cache_write_tokens=0,
        output_tokens=450, reasoning_tokens=80, seconds=3.1,
    )
    record(
        "log_usage",
        {"run_id": "smoke-run-1", "agent": "demo-agent", "input_tokens": 1200, "cached_tokens": 300,
         "cache_write_tokens": 0, "output_tokens": 450, "reasoning_tokens": 80, "seconds": 3.1},
        usage,
    )

    output = {
        "how_these_calls_were_made": (
            "Every tool function in mcp_server/server.py was called directly, in-process, in this "
            "Python script (tools/make_mcp_smoke.py) -- the same plain Python functions FastMCP "
            "registers as tools, not through the stdio MCP transport or an LLM client. This "
            "exercises the exact same code path a real MCP call would reach (the @mcp.tool() "
            "decorator does not wrap or alter the function), it's just not round-tripped over "
            "stdio for this smoke test. tests/test_mcp.py calls the same functions the same way "
            "and asserts on their results; this file just records them. The database was reloaded "
            "fresh (python -m backend.load) immediately before these calls. The 12 true rules "
            "(data/policy_rules_truth.json) were proposed and approved through the real "
            "propose_rule/approve_rule tools before the engine calls, and the TRUE line facts "
            "(data/requests_truth.json) were written directly into the lines table as a stand-in "
            "for the step04 Request Reader agent, which does not exist yet."
        ),
        "calls": calls,
    }
    OUTPUT.write_text(json.dumps(output, indent=2, default=str))
    print(f"wrote {OUTPUT} with {len(calls)} recorded tool calls")


if __name__ == "__main__":
    main()
