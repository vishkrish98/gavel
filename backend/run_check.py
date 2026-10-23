"""Command: python -m backend.run_check

Runs the full agent pipeline (CHAIR -> Policy Compiler -> Request Reader -> Skeptic -> Engine ->
consistency report -> Optimizer -> Drafter) over the 24 real requests and scores the result
against the answer key. Does NOT fix accuracy -- this is a measurement, reported honestly.
Saves the real numbers to evidence/ and the full ordered trace to output/trace_run1.json.
"""

from __future__ import annotations

import asyncio
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.chair import run_full_pipeline
from backend.db import get_connection
from backend.load import main as reload_fresh_db

DATA = ROOT / "data"
REAL_REQUEST_IDS = [f"Q{i:02d}" for i in range(1, 25)]


def score_rules(rules_info: dict) -> dict:
    truth = json.loads((DATA / "policy_rules_truth.json").read_text())
    decoy_paras = set(truth["decoy_paras"])
    truth_by_para = {r["para"]: r for r in truth["rules"]}

    conn = get_connection()
    approved_rows = conn.execute("SELECT * FROM rules WHERE status = 'approved'").fetchall()
    proposed_rows = conn.execute("SELECT * FROM rules").fetchall()
    conn.close()

    approved_by_para = {r["para_id"]: r for r in approved_rows}
    true_positives = sum(1 for para in truth_by_para if para in approved_by_para and approved_by_para[para]["type"] == truth_by_para[para]["type"])
    decoys_turned_into_rules = sum(1 for r in approved_rows if r["para_id"] in decoy_paras)

    recall = true_positives / len(truth_by_para) if truth_by_para else 0.0
    precision = true_positives / len(approved_rows) if approved_rows else 0.0

    quote_attempts = len(proposed_rows)
    quote_verified = sum(1 for r in proposed_rows if r["quote_verified"])

    return {
        "true_rules": len(truth_by_para),
        "approved_rules": len(approved_rows),
        "true_positives_by_para_and_type": true_positives,
        "recall": recall,
        "precision": precision,
        "decoy_paragraphs_turned_into_rules": decoys_turned_into_rules,
        "quote_attempts": quote_attempts,
        "quote_verified": quote_verified,
        "quote_validity_rate": (quote_verified / quote_attempts) if quote_attempts else 0.0,
        "compiler_summary": rules_info.get("summary"),
    }


def score_categories_and_verdicts(verdicts: dict) -> dict:
    truth = json.loads((DATA / "requests_truth.json").read_text())["requests"]
    conn = get_connection()
    line_rows = {row["id"]: row for row in conn.execute("SELECT * FROM lines")}
    conn.close()

    category_total: dict[str, int] = defaultdict(int)
    category_correct: dict[str, int] = defaultdict(int)
    verdict_total: dict[str, int] = defaultdict(int)
    verdict_correct: dict[str, int] = defaultdict(int)
    both_verdict_and_amount_correct = 0
    total_lines = 0
    total_allowed_computed = 0.0
    total_allowed_truth = 0.0
    abs_dollar_diff_sum = 0.0

    for request_id in REAL_REQUEST_IDS:
        for line_id, truth_facts in truth[request_id]["lines"].items():
            total_lines += 1
            true_category = truth_facts["category"]
            category_total[true_category] += 1
            reader_category = line_rows[line_id]["category"]
            if reader_category == true_category:
                category_correct[true_category] += 1

            true_verdict = truth_facts["verdict"]
            verdict_total[true_verdict] += 1
            pipeline = verdicts.get(line_id, {"verdict": None, "allowed_amount": None})
            if pipeline["verdict"] == true_verdict:
                verdict_correct[true_verdict] += 1
            if pipeline["verdict"] == true_verdict and pipeline["allowed_amount"] == truth_facts["allowed_amount"]:
                both_verdict_and_amount_correct += 1

            total_allowed_truth += truth_facts["allowed_amount"]
            if pipeline["allowed_amount"] is not None:
                total_allowed_computed += pipeline["allowed_amount"]
                abs_dollar_diff_sum += abs(pipeline["allowed_amount"] - truth_facts["allowed_amount"])

    category_accuracy = {cat: (category_correct[cat] / category_total[cat]) for cat in category_total}
    verdict_accuracy = {v: (verdict_correct[v] / verdict_total[v]) for v in verdict_total}
    overall_category_accuracy = sum(category_correct.values()) / total_lines if total_lines else 0.0
    overall_verdict_accuracy = sum(verdict_correct.values()) / total_lines if total_lines else 0.0

    return {
        "total_lines": total_lines,
        "category_accuracy_per_category": category_accuracy,
        "overall_category_accuracy": overall_category_accuracy,
        "verdict_accuracy_per_verdict_type": verdict_accuracy,
        "overall_verdict_accuracy": overall_verdict_accuracy,
        "both_verdict_and_amount_correct": both_verdict_and_amount_correct,
        "both_verdict_and_amount_correct_rate": both_verdict_and_amount_correct / total_lines if total_lines else 0.0,
        "total_allowed_computed": total_allowed_computed,
        "total_allowed_truth": total_allowed_truth,
        "allowed_dollar_accuracy": 1 - (abs(total_allowed_computed - total_allowed_truth) / total_allowed_truth) if total_allowed_truth else 0.0,
        "mean_absolute_dollar_diff_per_line": abs_dollar_diff_sum / total_lines if total_lines else 0.0,
    }


def score_skeptic(verdicts: dict) -> dict:
    truth = json.loads((DATA / "requests_truth.json").read_text())["requests"]
    conn = get_connection()
    line_rows = {row["id"]: row for row in conn.execute("SELECT * FROM lines")}
    conn.close()

    flagged = [line_id for line_id, v in verdicts.items() if v.get("flagged_for_review")]
    true_positives = 0  # flagged AND Reader's category was actually wrong
    false_positives = 0  # flagged but Reader's category was actually right
    for line_id in flagged:
        request_id = line_rows[line_id]["request_id"]
        true_category = truth[request_id]["lines"][line_id]["category"]
        if line_rows[line_id]["category"] != true_category:
            true_positives += 1
        else:
            false_positives += 1

    return {
        "lines_flagged": len(flagged),
        "flagged_that_were_actual_misclassifications": true_positives,
        "flagged_that_were_not_actual_errors": false_positives,
        "flagged_line_ids": flagged,
    }


def score_consistency(live_consistency: dict) -> dict:
    """Compares the live pipeline's consistency_report (model-derived facts) against the
    evidence/engine_eval.json baseline from step03 (true-fixture facts), decision by decision."""
    baseline_path = ROOT / "evidence" / "engine_eval.json"
    if not baseline_path.exists():
        return {"note": "evidence/engine_eval.json (step03) not found -- run step03 first for a baseline", "live": live_consistency}
    baseline = json.loads(baseline_path.read_text())["consistency_report"]
    baseline_by_id = {d["decision_id"]: d for d in baseline["decisions"]}

    agree = 0
    compared = 0
    for decision in live_consistency["decisions"]:
        baseline_decision = baseline_by_id.get(decision["decision_id"])
        if baseline_decision is None or not baseline_decision["matched"] or not decision["matched"]:
            continue
        compared += 1
        if decision["inconsistent"] == baseline_decision["inconsistent"]:
            agree += 1

    return {
        "live_inconsistent_count": live_consistency["inconsistent_count"],
        "live_matched": live_consistency["matched"],
        "baseline_inconsistent_count_from_step03": baseline["inconsistent_count"],
        "decisions_compared": compared,
        "decisions_agreeing_with_step03_baseline": agree,
        "agreement_rate": (agree / compared) if compared else 0.0,
    }


async def main() -> None:
    reload_fresh_db()
    result = await run_full_pipeline(REAL_REQUEST_IDS, benchmark_mode=True, run_id="run1")

    print(f"status: {result['status']}" + (f" (reason: {result['reason']})" if result["reason"] else ""))
    print(f"total tokens used: {result['total_tokens_used']}")

    rules_score = score_rules(result["rules_info"])
    category_verdict_score = score_categories_and_verdicts(result["verdicts"])
    skeptic_score = score_skeptic(result["verdicts"])
    consistency_score = score_consistency(result["consistency"]) if result["consistency"] else {}

    report = {
        "run_id": result["run_id"],
        "status": result["status"],
        "reason": result["reason"],
        "total_tokens_used": result["total_tokens_used"],
        "reader_errors": result["reader_errors"],
        "rules": rules_score,
        "categories_and_verdicts": category_verdict_score,
        "skeptic": skeptic_score,
        "consistency": consistency_score,
        "allocation_scenario_alpha_0.5": result["allocation"],
        "drafts_produced": {
            "question_drafts": len(result["drafts"].get("question_drafts", [])),
            "memo_draft_id": result["drafts"].get("memo_draft_id"),
        },
    }
    (ROOT / "evidence" / "run_check.json").write_text(json.dumps(report, indent=2, default=str))
    (ROOT / "output" / "trace_run1.json").write_text(json.dumps(result["trace"], indent=2, default=str))

    print(json.dumps({k: v for k, v in report.items() if k not in ("drafts_produced",)}, indent=2, default=str))
    print(f"\nwrote evidence/run_check.json and output/trace_run1.json ({len(result['trace'])} trace events)")


if __name__ == "__main__":
    asyncio.run(main())
