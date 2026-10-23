"""The deterministic rule engine. No model calls anywhere in this file.

Reproduces tools/make_funding_data.py's eval_line / run_engine / allocate, but generalized over
whatever rules are currently APPROVED in the `rules` table (type + JSON params) instead of a
hardcoded R01-R12 list -- the real rules only exist once the Policy Compiler proposes them and a
human approves them (step04). The order rule TYPES are checked in is fixed and mirrors the
reference eval_line exactly; see PROMPTS/step02_mcp_tools.md and PROMPTS/step03_engine.md.
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from typing import Any, Optional

# Fixed check order, matching tools/make_funding_data.py's eval_line top-to-bottom.
RULE_TYPE_ORDER = [
    "deadline",
    "retroactive_prohibit",
    "prohibited_category",
    "unit_threshold_prohibit",
    "unit_cap",
    "per_person_cap",
    "per_night_cap",
    "event_cap",
    "requires_docs",
    "semester_cap",
]


def _group_by_type(approved_rules: list[dict]) -> dict[str, list[dict]]:
    by_type: dict[str, list[dict]] = defaultdict(list)
    for rule in approved_rules:
        by_type[rule["type"]].append(rule)
    return by_type


def eval_line(line: dict[str, Any], request: dict[str, Any], approved_rules: list[dict], remaining: float) -> dict:
    """line needs: amount, category, headcount, qty, nights, unit_cost, docs (list), already_purchased.
    request needs: event_date, submitted_date (ISO strings).
    approved_rules: [{id, type, params: {...}}, ...] -- only rules with status == 'approved'.
    remaining: semester budget left for this request's club, before this line.
    Returns {"verdict": ..., "allowed_amount": ..., "rules": [rule_id, ...]}.
    """
    amount = line["amount"]
    category = line["category"]
    hits: list[str] = []
    allowed = amount
    verdict = "allowed"

    by_type = _group_by_type(approved_rules)

    for rule in by_type.get("deadline", []):
        days = (dt.date.fromisoformat(request["event_date"]) - dt.date.fromisoformat(request["submitted_date"])).days
        if days < rule["params"]["days"]:
            return {"verdict": "denied", "allowed_amount": 0, "rules": [rule["id"]]}

    for rule in by_type.get("retroactive_prohibit", []):
        if line["already_purchased"]:
            return {"verdict": "denied", "allowed_amount": 0, "rules": [rule["id"]]}

    for rule in by_type.get("prohibited_category", []):
        if category == rule["params"]["category"]:
            return {"verdict": "denied", "allowed_amount": 0, "rules": [rule["id"]]}

    for rule in by_type.get("unit_threshold_prohibit", []):
        if category == rule["params"]["category"] and line["unit_cost"] > rule["params"]["threshold"]:
            return {"verdict": "denied", "allowed_amount": 0, "rules": [rule["id"]]}

    for rule in by_type.get("unit_cap", []):
        if category == rule["params"]["category"] and line["unit_cost"] > rule["params"]["cap"]:
            allowed = rule["params"]["cap"] * line["qty"]
            hits.append(rule["id"])

    for rule in by_type.get("per_person_cap", []):
        if category == rule["params"]["category"] and amount > rule["params"]["cap"] * line["headcount"]:
            allowed = rule["params"]["cap"] * line["headcount"]
            hits.append(rule["id"])

    for rule in by_type.get("per_night_cap", []):
        if category == rule["params"]["category"] and line["unit_cost"] > rule["params"]["cap"]:
            allowed = rule["params"]["cap"] * line["qty"] * line["nights"]
            hits.append(rule["id"])

    for rule in by_type.get("event_cap", []):
        if category != rule["params"]["category"]:
            continue
        doc = rule["params"].get("doc")
        if doc and doc not in line["docs"]:
            return {"verdict": "needs_docs", "allowed_amount": 0, "rules": [rule["id"]]}
        if amount > rule["params"]["cap"]:
            allowed = rule["params"]["cap"]
            hits.append(rule["id"])

    for rule in by_type.get("requires_docs", []):
        threshold = rule["params"]["threshold"]
        doc = rule["params"]["doc"]
        # Mirrors the reference's quirky condition exactly: for "equipment" lines the trigger is
        # amount > threshold AND unit_cost > threshold; for everything else it's just amount > threshold.
        if category == "equipment":
            triggered = amount > threshold and line["unit_cost"] > threshold
        else:
            triggered = amount > threshold
        if triggered and doc not in line["docs"]:
            return {"verdict": "needs_docs", "allowed_amount": 0, "rules": [rule["id"]]}

    if hits:
        verdict = "reduced"

    for rule in by_type.get("semester_cap", []):
        if allowed > remaining:
            allowed = max(remaining, 0)
            hits.append(rule["id"])
            verdict = "reduced" if allowed > 0 else "denied"

    return {"verdict": verdict, "allowed_amount": allowed, "rules": hits}


def run_engine_for_lines(
    request: dict[str, Any], lines: list[dict[str, Any]], approved_rules: list[dict]
) -> dict[str, dict]:
    """Evaluate every line of one request, in order, tracking the semester-cap remaining budget
    across them (mirrors tools/make_funding_data.py's run_engine, which resets rem=cap once per
    request -- correct here because every club in this dataset submits exactly one request)."""
    semester_caps = [r["params"]["cap"] for r in approved_rules if r["type"] == "semester_cap"]
    remaining = semester_caps[0] if semester_caps else float("inf")
    results: dict[str, dict] = {}
    for line in lines:
        result = eval_line(line, request, approved_rules, remaining)
        remaining -= result["allowed_amount"]
        results[line["id"] if "id" in line else line["line_id"]] = result
    return results


def allocate(allowed: dict[str, float], util: dict[str, float], pot: float, alpha: float) -> dict[str, float]:
    """Water-filling optimizer, ported verbatim from tools/make_funding_data.py's allocate().
    Weight = allowed * (1 - alpha + alpha * utilization); capped at the club's own allowed amount."""
    weights = {c: allowed[c] * (1 - alpha + alpha * util.get(c, 0.0)) for c in allowed}
    alloc = {c: 0.0 for c in allowed}
    open_clubs = {c for c in allowed if allowed[c] > 0}
    left = pot
    while open_clubs and left > 1e-6:
        total_weight = sum(weights[c] for c in open_clubs)
        done = set()
        spent = 0.0
        for c in open_clubs:
            share = left * weights[c] / total_weight
            room = allowed[c] - alloc[c]
            if share >= room - 1e-9:
                alloc[c] += room
                spent += room
                done.add(c)
        if not done:
            for c in open_clubs:
                alloc[c] += left * weights[c] / total_weight
            left = 0
            break
        left -= spent
        open_clubs -= done
    return {c: round(v, 2) for c, v in alloc.items()}
