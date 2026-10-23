"""Turns measured usage data (the `usage` table, written by every model call -- see
mcp_server/server.py's log_usage and backend/chair.py's _call_agent) into a cost projection.
Every number that isn't measured from a real run is an assumption, and every assumption lives in
the ASSUMPTIONS block below -- nowhere else in this file hardcodes a number that isn't derived
from either ASSUMPTIONS or the measured usage table.

Run with: python -m backend.projection [run_id]  (default run_id: "run1")
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.db import get_connection

# ---------------------------------------------------------------------------
# ASSUMPTIONS -- change these, nothing else, to re-run the projection under different scenarios.
# ---------------------------------------------------------------------------
ASSUMPTIONS = {
    "clubs_small": 24,  # MEASURED: the actual number of clubs/requests in this project's dataset.
    "clubs_medium": 150,  # ASSUMPTION: a larger student government, same request/line patterns as our sample.
    "platform_institutions": 1000,  # ASSUMPTION: a platform serving 1,000 institutions.
    "requests_per_club_per_semester": 1,  # ASSUMPTION: matches this dataset (24 clubs -> 24 requests).
    "institution_size_for_platform_clubs": 24,  # ASSUMPTION: each platform institution looks like our 24-club sample (its own policy, its own compile cost).
    "reviewer_minutes_per_request": 20,  # ASSUMPTION: a committee member's time to manually review one request by hand.
    "reviewer_hourly_rate_usd": 20.0,  # ASSUMPTION: a student-worker/stipend hourly rate for a committee reviewer.
}


def agent_family(agent_name: str) -> str:
    """Strips the ':Q01'-style per-request suffix off an agent name, e.g. 'skeptic:Q03' -> 'skeptic'."""
    return agent_name.split(":", 1)[0]


def load_usage(run_id: str) -> list[dict]:
    conn = get_connection()
    rows = [dict(r) for r in conn.execute("SELECT * FROM usage WHERE run_id = ?", (run_id,))]
    conn.close()
    if not rows:
        raise ValueError(f"no usage rows for run_id={run_id!r} -- run the pipeline first (python -m backend.run_check)")
    return rows


def load_line_count(run_id: str) -> int:
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM verdicts WHERE run_id = ?", (run_id,)).fetchone()[0]
    conn.close()
    return count


def build_cost_model(run_id: str) -> dict:
    rows = load_usage(run_id)
    line_count = load_line_count(run_id)

    by_family: dict[str, list[dict]] = {}
    for row in rows:
        by_family.setdefault(agent_family(row["agent"]), []).append(row)

    def family_cost(name: str) -> float:
        return sum(r["cost_usd"] for r in by_family.get(name, []))

    def family_tokens(name: str) -> int:
        return sum(r["total_tokens"] for r in by_family.get(name, []))

    clubs = ASSUMPTIONS["clubs_small"]
    requests = clubs * ASSUMPTIONS["requests_per_club_per_semester"]
    if requests == 0:
        raise ValueError("clubs_small * requests_per_club_per_semester must be > 0")

    # One-time-per-semester costs: compiling the policy once, and the one whole-pot memo.
    # Everything else (Reader, Skeptic, Drafter-questions) scales with the number of requests.
    cost_to_compile_policy_once = family_cost("policy_compiler")
    cost_of_memo_once = family_cost("drafter_memo")
    per_request_family_cost = family_cost("request_reader") + family_cost("skeptic") + family_cost("drafter_questions")
    cost_per_request = per_request_family_cost / requests
    cost_per_line_item = (per_request_family_cost / line_count) if line_count else 0.0

    measured_total_cost = sum(r["cost_usd"] for r in rows)
    measured_total_tokens = sum(r["total_tokens"] for r in rows)

    def semester_cost_for(num_clubs: int) -> float:
        num_requests = num_clubs * ASSUMPTIONS["requests_per_club_per_semester"]
        return cost_to_compile_policy_once + cost_of_memo_once + num_requests * cost_per_request

    semester_small = semester_cost_for(clubs)
    semester_medium = semester_cost_for(ASSUMPTIONS["clubs_medium"])
    # Platform: each institution runs its own compile + its own semester of requests (its own
    # policy, so its own one-time compile cost -- not shared across institutions).
    per_institution_cost = semester_cost_for(ASSUMPTIONS["institution_size_for_platform_clubs"])
    platform_total_cost = ASSUMPTIONS["platform_institutions"] * per_institution_cost

    reviewer_cost_per_request = (ASSUMPTIONS["reviewer_minutes_per_request"] / 60.0) * ASSUMPTIONS["reviewer_hourly_rate_usd"]
    reviewer_cost_small = reviewer_cost_per_request * requests
    reviewer_cost_medium = reviewer_cost_per_request * (ASSUMPTIONS["clubs_medium"] * ASSUMPTIONS["requests_per_club_per_semester"])

    return {
        "run_id": run_id,
        "assumptions": ASSUMPTIONS,
        "measured": {
            "total_cost_usd": measured_total_cost,
            "total_tokens": measured_total_tokens,
            "model_calls": len(rows),
            "lines_scored": line_count,
            "by_family_cost_usd": {name: round(family_cost(name), 6) for name in by_family},
            "by_family_tokens": {name: family_tokens(name) for name in by_family},
        },
        "unit_costs": {
            "cost_to_compile_one_policy_usd": round(cost_to_compile_policy_once, 6),
            "cost_of_one_whole_pot_memo_usd": round(cost_of_memo_once, 6),
            "cost_per_request_usd": round(cost_per_request, 6),
            "cost_per_line_item_usd": round(cost_per_line_item, 6),
        },
        "semester_projections_usd": {
            f"{clubs}_clubs_measured": round(semester_small, 4),
            f"{ASSUMPTIONS['clubs_medium']}_clubs_assumption": round(semester_medium, 4),
            f"platform_{ASSUMPTIONS['platform_institutions']}_institutions_assumption": round(platform_total_cost, 2),
        },
        "human_comparison_usd": {
            "reviewer_cost_per_request": round(reviewer_cost_per_request, 2),
            f"reviewer_cost_{clubs}_requests": round(reviewer_cost_small, 2),
            f"reviewer_cost_{ASSUMPTIONS['clubs_medium']}_requests": round(reviewer_cost_medium, 2),
            "pipeline_cost_per_request": round(cost_per_request, 6),
            "note": (
                "This compares the AI pipeline's per-request cost to the cost of one committee "
                "member's manual review time at the assumed rate. It is NOT a claim that Gavel "
                "replaces that review -- the committee still makes every decision (CONTEXT.md hard "
                "rule 10). The honest comparison is the cost of Gavel's first-pass packet (rule "
                "citations, verdicts, flagged lines, drafted questions) against the cost of a human "
                "producing the same thing from scratch."
            ),
        },
    }


def write_markdown(model: dict, path: Path) -> None:
    a = model["assumptions"]
    m = model["measured"]
    u = model["unit_costs"]
    s = model["semester_projections_usd"]
    h = model["human_comparison_usd"]

    lines = [
        "# Gavel cost model",
        "",
        f"Built from real measured usage for run `{model['run_id']}` "
        f"({m['model_calls']} model calls, {m['total_tokens']:,} tokens, ${m['total_cost_usd']:.4f} total, "
        f"{m['lines_scored']} lines scored). No token count here is estimated -- every number comes "
        "from the `usage` table, written once per real model call from the provider's own response fields.",
        "",
        "## Assumptions (change these to re-run)",
        "",
        "| Assumption | Value | Status |",
        "| --- | --- | --- |",
    ]
    labels = {
        "clubs_small": "Clubs in this project's dataset",
        "clubs_medium": "Clubs, larger student government",
        "platform_institutions": "Institutions on a shared platform",
        "requests_per_club_per_semester": "Requests per club per semester",
        "institution_size_for_platform_clubs": "Clubs per platform institution",
        "reviewer_minutes_per_request": "Reviewer minutes per request (manual)",
        "reviewer_hourly_rate_usd": "Reviewer hourly rate (USD)",
    }
    measured_keys = {"clubs_small"}
    for key, value in a.items():
        status = "measured" if key in measured_keys else "**assumption**"
        lines.append(f"| {labels.get(key, key)} | {value} | {status} |")

    lines += [
        "",
        "## Unit costs (measured, from run above)",
        "",
        "| Unit | Cost (USD) |",
        "| --- | --- |",
        f"| Compile one policy (once per semester) | ${u['cost_to_compile_one_policy_usd']:.6f} |",
        f"| One whole-pot decision memo (once per semester) | ${u['cost_of_one_whole_pot_memo_usd']:.6f} |",
        f"| Per request (Reader + Skeptic + drafted questions) | ${u['cost_per_request_usd']:.6f} |",
        f"| Per line item | ${u['cost_per_line_item_usd']:.6f} |",
        "",
        "## Semester cost projections (USD)",
        "",
        "| Scenario | Total cost | Status |",
        "| --- | --- | --- |",
    ]
    for key, value in s.items():
        status = "measured" if "measured" in key else "**assumption**"
        lines.append(f"| {key.replace('_', ' ')} | ${value:,.4f} | {status} |")

    small_clubs_key = f"reviewer_cost_{a['clubs_small']}_requests"
    medium_clubs_key = f"reviewer_cost_{a['clubs_medium']}_requests"
    reviewer_cost_small = h[small_clubs_key]
    reviewer_cost_medium = h[medium_clubs_key]
    pipeline_cost_small = h["pipeline_cost_per_request"] * a["clubs_small"]
    pipeline_cost_medium = h["pipeline_cost_per_request"] * a["clubs_medium"]

    lines += [
        "",
        "## Human comparison (assumption-labeled)",
        "",
        f"Assumed {a['reviewer_minutes_per_request']} minutes/request at ${a['reviewer_hourly_rate_usd']:.2f}/hour "
        f"= **${h['reviewer_cost_per_request']:.2f}/request** for one manual review.",
        "",
        "| Scale | Human reviewer cost | Gavel pipeline cost | Status |",
        "| --- | --- | --- | --- |",
        f"| {a['clubs_small']} requests (measured scale) | ${reviewer_cost_small:,.2f} | ${pipeline_cost_small:,.4f} | measured scale, assumed rate |",
        f"| {a['clubs_medium']} requests | ${reviewer_cost_medium:,.2f} | ${pipeline_cost_medium:,.4f} | **assumption** |",
        "",
        f"> {h['note']}",
        "",
        "## Per-agent breakdown (measured)",
        "",
        "| Agent | Cost (USD) | Tokens |",
        "| --- | --- | --- |",
    ]
    for name in m["by_family_cost_usd"]:
        lines.append(f"| {name} | ${m['by_family_cost_usd'][name]:.6f} | {m['by_family_tokens'][name]:,} |")

    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    run_id = sys.argv[1] if len(sys.argv) > 1 else "run1"
    model = build_cost_model(run_id)
    out_path = ROOT / "evidence" / "cost_model.md"
    write_markdown(model, out_path)
    print(f"wrote {out_path}")
    print(f"measured total: {model['measured']['model_calls']} calls, "
          f"{model['measured']['total_tokens']} tokens, ${model['measured']['total_cost_usd']:.4f}")
    print(f"unit costs: {model['unit_costs']}")
    print(f"semester projections: {model['semester_projections_usd']}")


if __name__ == "__main__":
    main()
