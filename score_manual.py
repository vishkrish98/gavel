"""Scores the user's hand-filled manual baseline (evidence/manual_first5.csv) against the same
answer key used everywhere else in this project (data/requests_truth.json), for Q01-Q05 only.
This is Mode C in step06's benchmark terminology -- the human baseline -- scored the same way as
Mode A and Mode B so the comparison is apples to apples.

evidence/manual_first5.csv must have the header from evidence/manual_first5_TEMPLATE.csv:
    request_id,line_id,verdict,allowed_amount,rule_para

Run with: python -m score_manual
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DATA = ROOT / "data"
MANUAL_CSV = ROOT / "evidence" / "manual_first5.csv"
TEMPLATE_CSV = ROOT / "evidence" / "manual_first5_TEMPLATE.csv"
REQUEST_IDS = ["Q01", "Q02", "Q03", "Q04", "Q05"]


def load_truth() -> tuple[dict, dict]:
    truth = json.loads((DATA / "requests_truth.json").read_text())["requests"]
    line_truth: dict[str, dict] = {}
    for request_id in REQUEST_IDS:
        line_truth.update(truth[request_id]["lines"])
    ruleid_to_para = {r["rule_id"]: r["para"] for r in json.loads((DATA / "policy_rules_truth.json").read_text())["rules"]}
    return line_truth, ruleid_to_para


def load_manual() -> list[dict]:
    if not MANUAL_CSV.exists():
        line_truth, _ = load_truth()
        raise SystemExit(
            f"{MANUAL_CSV} does not exist yet.\n\n"
            f"This is your own timed, by-hand review (see START_HERE.md task #1 and "
            f"evidence/manual_first5_requests.txt for Q01-Q05's details): fill in "
            f"{TEMPLATE_CSV} with columns request_id,line_id,verdict,allowed_amount,rule_para "
            f"for all {len(line_truth)} lines across Q01-Q05 (without looking at any answer key "
            f"or app output), save it as evidence/manual_first5.csv, and re-run this script."
        )
    with MANUAL_CSV.open(newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise SystemExit(f"{MANUAL_CSV} exists but has no data rows (only the header, or is empty).")
    return rows


def main() -> None:
    line_truth, ruleid_to_para = load_truth()
    manual_rows = load_manual()

    manual_by_line = {}
    for row in manual_rows:
        line_id = row["line_id"].strip()
        if not line_id:
            continue
        manual_by_line[line_id] = row

    verdict_total = 0
    verdict_correct = 0
    abs_dollar_diff = 0.0
    wrongly_allowed_dollars = 0.0
    wrongly_allowed_count = 0
    missing_lines = []
    per_line = []
    citation_correct = 0
    citation_checked = 0

    for line_id, truth in line_truth.items():
        verdict_total += 1
        manual = manual_by_line.get(line_id)
        if manual is None:
            missing_lines.append(line_id)
            per_line.append({"line_id": line_id, "status": "missing_from_manual_csv", "truth": truth})
            continue

        try:
            manual_allowed = float(manual["allowed_amount"]) if manual.get("allowed_amount", "").strip() else 0.0
        except ValueError:
            manual_allowed = 0.0
        manual_verdict = manual.get("verdict", "").strip()

        verdict_ok = manual_verdict == truth["verdict"]
        if verdict_ok:
            verdict_correct += 1
        abs_dollar_diff += abs(manual_allowed - truth["allowed_amount"])
        if manual_allowed > truth["allowed_amount"]:
            wrongly_allowed_dollars += manual_allowed - truth["allowed_amount"]
        if manual_verdict == "allowed" and truth["verdict"] != "allowed":
            wrongly_allowed_count += 1

        expected_paras = {ruleid_to_para[r] for r in truth["rules"] if r in ruleid_to_para}
        manual_para = (manual.get("rule_para") or "").strip()
        if expected_paras:
            citation_checked += 1
            if manual_para in expected_paras:
                citation_correct += 1

        per_line.append(
            {
                "line_id": line_id,
                "status": "ok" if verdict_ok else "verdict_mismatch",
                "manual": {"verdict": manual_verdict, "allowed_amount": manual_allowed, "rule_para": manual_para},
                "truth": {"verdict": truth["verdict"], "allowed_amount": truth["allowed_amount"], "rule_paras": sorted(expected_paras)},
            }
        )

    result = {
        "note": "Mode C (human baseline), scored against the same data/requests_truth.json used for Mode A/B in step06.",
        "lines_scored": verdict_total,
        "lines_missing_from_manual_csv": missing_lines,
        "overall_verdict_accuracy": verdict_correct / verdict_total if verdict_total else 0.0,
        "sum_abs_dollar_diff": round(abs_dollar_diff, 2),
        "total_dollars_wrongly_allowed": round(wrongly_allowed_dollars, 2),
        "lines_wrongly_allowed_that_should_be_denied_or_reduced": wrongly_allowed_count,
        "rule_citation_accuracy": (citation_correct / citation_checked) if citation_checked else None,
        "rule_citations_checked": citation_checked,
        "per_line": per_line,
    }

    out_path = ROOT / "evidence" / "manual_first5_scored.json"
    out_path.write_text(json.dumps(result, indent=2, default=str))

    print(f"Lines scored: {result['lines_scored']} (missing from your CSV: {len(missing_lines)})")
    print(f"Verdict accuracy: {result['overall_verdict_accuracy']:.3f}")
    print(f"Sum |allowed-dollar error|: ${result['sum_abs_dollar_diff']:.2f}")
    print(f"Total $ wrongly allowed: ${result['total_dollars_wrongly_allowed']:.2f}")
    print(f"Rule citation accuracy: {result['rule_citation_accuracy']}")
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()
