"""Club registry: bulk-import clubs with a pre-approved budget, and compute each club's running
balance (pre-approved budget minus every allowed/reduced dollar from the latest run touching that
club). Joins to requests/verdicts by club NAME, the same convention backend/engine.py's
consistency check and the optimizer already use for requests.club -- deliberately not a foreign
key, so this stays additive to the existing schema rather than a migration of it.
"""

from __future__ import annotations

import sqlite3
import uuid


class ClubValidationError(ValueError):
    pass


def _validate_club(club: dict) -> None:
    if not club.get("name"):
        raise ClubValidationError("Each club needs a `name`.")
    budget = club.get("pre_approved_budget", 0)
    try:
        float(budget)
    except (TypeError, ValueError):
        raise ClubValidationError(f"Club {club['name']!r}: `pre_approved_budget` must be a number.")


def upsert_club(conn: sqlite3.Connection, club: dict) -> str:
    """Inserts a club, or updates it in place if a club with that name already exists (bulk
    imports are expected to be re-run as budgets change year to year)."""
    _validate_club(club)
    existing = conn.execute("SELECT id FROM clubs WHERE name = ?", (club["name"],)).fetchone()
    club_id = existing["id"] if existing else f"club-{uuid.uuid4().hex[:8]}"
    conn.execute(
        """INSERT INTO clubs (id, name, category, pre_approved_budget, notes)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(name) DO UPDATE SET
             category = excluded.category,
             pre_approved_budget = excluded.pre_approved_budget,
             notes = excluded.notes""",
        (
            club_id,
            club["name"],
            club.get("category"),
            float(club.get("pre_approved_budget", 0)),
            club.get("notes"),
        ),
    )
    return club_id


def import_clubs_bulk(conn: sqlite3.Connection, clubs: list[dict]) -> dict:
    """Validates every club first (all-or-nothing), then upserts. Returns a summary rather than
    raising on the first bad row, so a bulk import's caller can report every problem at once."""
    if not isinstance(clubs, list) or not clubs:
        raise ClubValidationError("Provide a non-empty list of clubs.")
    errors: list[str] = []
    for i, club in enumerate(clubs):
        try:
            _validate_club(club)
        except ClubValidationError as exc:
            errors.append(f"Row {i + 1}: {exc}")
    if errors:
        raise ClubValidationError("; ".join(errors))

    ids = [upsert_club(conn, club) for club in clubs]
    conn.commit()
    return {"imported": len(ids), "club_ids": ids}


def list_clubs_with_balances(conn: sqlite3.Connection, run_id: str | None = None) -> list[dict]:
    """Each club's running balance = pre_approved_budget minus every allowed_amount for that
    club's lines in the given run (or, if run_id is omitted, the most recent run touching each
    club). A club with no requests yet, or no run yet, shows its full pre-approved budget."""
    clubs = [dict(r) for r in conn.execute("SELECT * FROM clubs ORDER BY name")]
    for club in clubs:
        if run_id:
            row = conn.execute(
                """SELECT COALESCE(SUM(v.allowed_amount), 0) AS spent, COUNT(*) AS lines
                   FROM verdicts v
                   JOIN lines l ON l.id = v.line_id
                   JOIN requests r ON r.id = l.request_id
                   WHERE r.club = ? AND v.run_id = ?""",
                (club["name"], run_id),
            ).fetchone()
        else:
            row = conn.execute(
                """SELECT COALESCE(SUM(v.allowed_amount), 0) AS spent, COUNT(*) AS lines
                   FROM verdicts v
                   JOIN lines l ON l.id = v.line_id
                   JOIN requests r ON r.id = l.request_id
                   WHERE r.club = ? AND v.run_id = (
                       SELECT run_id FROM verdicts v2
                       JOIN lines l2 ON l2.id = v2.line_id
                       JOIN requests r2 ON r2.id = l2.request_id
                       WHERE r2.club = ?
                       ORDER BY v2.rowid DESC LIMIT 1
                   )""",
                (club["name"], club["name"]),
            ).fetchone()
        spent = row["spent"] if row else 0.0
        club["spent"] = spent
        club["remaining_balance"] = round(club["pre_approved_budget"] - spent, 2)
        club["lines_reviewed"] = row["lines"] if row else 0
    return clubs
