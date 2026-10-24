"""Gavel data loader. Run with:  python -m backend.load

Reads the synthetic policy, the 24 real requests, the 2 JSON safety requests, and the 1 HTML
safety request, and loads them into data/gavel.db (created fresh each run -- see db.init_db).

What is deliberately NOT loaded:
- policy_rules_truth.json, requests_truth.json, optimizer_truth.json: answer keys, read only by
  the benchmark/eval code in later steps, never by anything the agents can see.
- prior_decisions.json's `inconsistent` and `policy_allowed` fields: also answer-key fields for
  the step03 consistency check.
- lines load WITHOUT category/headcount/qty/nights -- classifying each line is the Request
  Reader agent's job (step04), not the data layer's.
- club_history.json is read and validated here (so a bad file fails loudly at load time) but not
  persisted to its own table: no table for it is in the step01 schema, and the optimizer (step06)
  reads it directly from data/ the same way the reference engine in tools/make_funding_data.py does.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend import db
from backend.hidden_html import parse_hidden_request

DATA = ROOT / "data"

PARA_RE = re.compile(r"^(\d+\.\d+)\s+(.*)$")


def load_policy_text_into_db(conn, text: str) -> int:
    """Parses paragraphs of the form '3.1  Some text...' and inserts them. Shared by the step01
    loader (the bundled sample policy) and POST /api/policy (step08a, an uploaded/pasted policy)."""
    count = 0
    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = PARA_RE.match(line)
        if not match:
            continue
        para_id, para_text = match.group(1), match.group(2).strip()
        # kind is intentionally left NULL here: whether a paragraph is a rule, guidance, or info
        # is exactly what the Policy Compiler agent (step04) has to figure out from the raw text.
        # Labeling it at load time would leak the decoy-paragraph answer into the data layer.
        conn.execute(
            "INSERT INTO policy_paragraphs (para_id, text, kind) VALUES (?, ?, NULL)",
            (para_id, para_text),
        )
        count += 1
    return count


def load_policy_paragraphs(conn) -> int:
    text = (DATA / "policy_synthetic.txt").read_text()
    return load_policy_text_into_db(conn, text)


def _insert_request(conn, request: dict, source: str) -> int:
    conn.execute(
        "INSERT INTO requests (id, club, event_date, submitted_date, justification, source) VALUES (?, ?, ?, ?, ?, ?)",
        (
            request["request_id"],
            request["club"],
            request["event_date"],
            request["submitted_date"],
            request["justification"],
            source,
        ),
    )
    line_count = 0
    for line in request["lines"]:
        conn.execute(
            """INSERT INTO lines
               (id, request_id, description, amount, docs_json, already_purchased,
                category, headcount, qty, nights, unit_cost, quarantined)
               VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, NULL, NULL, NULL, 0)""",
            (
                line["line_id"],
                request["request_id"],
                line["description"],
                line["amount"],
                json.dumps(line.get("docs", [])),
                1 if line.get("already_purchased") else 0,
            ),
        )
        line_count += 1
    return line_count


def load_requests(conn) -> tuple[int, int]:
    requests = json.loads((DATA / "requests_input.json").read_text())
    total_lines = 0
    for request in requests:
        total_lines += _insert_request(conn, request, source="requests_input.json")
    return len(requests), total_lines


def load_safety_requests(conn) -> tuple[int, int]:
    requests = json.loads((DATA / "safety_requests.json").read_text())
    total_lines = 0
    for request in requests:
        total_lines += _insert_request(conn, request, source="safety_requests.json")
    return len(requests), total_lines


def load_hidden_html_request(conn) -> tuple[int, list[dict[str, str]]]:
    request, hidden_flags = parse_hidden_request(DATA / "safety_request_hidden.html")
    line_count = _insert_request(conn, request, source="safety_request_hidden.html")
    # Persisted (step07) so backend/safety.py can look up what hidden text was found for a given
    # request without re-parsing the HTML or hardcoding a filename.
    for flag in hidden_flags:
        conn.execute(
            "INSERT INTO hidden_text_flags (request_id, tag, reason, text) VALUES (?, ?, ?, ?)",
            (request["request_id"], flag["tag"], flag["reason"], flag["text"]),
        )
    return line_count, hidden_flags


def load_prior_decisions(conn) -> int:
    payload = json.loads((DATA / "prior_decisions.json").read_text())
    count = 0
    for decision in payload["decisions"]:
        # Deliberately NOT reading decision["inconsistent"] or decision["policy_allowed"] --
        # those are answer-key fields for step03's consistency check (see module docstring).
        conn.execute(
            """INSERT INTO prior_decisions (id, club, description, requested, approved, docs_json, term)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                decision["decision_id"],
                decision["club"],
                decision["description"],
                decision["requested"],
                decision["approved"],
                json.dumps(decision.get("docs", [])),
                decision.get("term"),
            ),
        )
        count += 1
    return count


def validate_club_history() -> int:
    """Read-only sanity check; not persisted (see module docstring)."""
    payload = json.loads((DATA / "club_history.json").read_text())
    assert "pot" in payload and "clubs" in payload, "club_history.json missing pot or clubs"
    return len(payload["clubs"])


def main() -> None:
    conn = db.get_connection()
    db.init_db(conn, fresh=True)

    n_paragraphs = load_policy_paragraphs(conn)
    n_requests, n_lines = load_requests(conn)
    n_safety_requests, n_safety_lines = load_safety_requests(conn)
    n_html_lines, hidden_flags = load_hidden_html_request(conn)
    n_prior = load_prior_decisions(conn)
    n_clubs = validate_club_history()

    conn.commit()
    conn.close()

    print(f"policy paragraphs: {n_paragraphs}")
    print(f"requests: {n_requests} plus {n_safety_requests} safety plus 1 HTML = {n_requests + n_safety_requests + 1}")
    print(
        f"lines: {n_lines} plus {n_safety_lines} safety lines plus {n_html_lines} HTML lines "
        f"= {n_lines + n_safety_lines + n_html_lines}"
    )
    print(f"prior decisions: {n_prior}")
    print(f"hidden text flags in HTML request: {len(hidden_flags)}")
    print(f"club_history.json validated: {n_clubs} clubs (not persisted, no table for it)")


if __name__ == "__main__":
    main()
