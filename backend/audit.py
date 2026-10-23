"""Append-only audit log helper. Only ever INSERTs into the `audit` table -- no function in this
module (or anywhere else in the codebase) should UPDATE or DELETE a row in it.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone


def log_event(conn: sqlite3.Connection, run_id: str | None, event: str, detail: dict | None = None) -> None:
    conn.execute(
        "INSERT INTO audit (run_id, ts, event, detail_json) VALUES (?, ?, ?, ?)",
        (run_id, datetime.now(timezone.utc).isoformat(), event, json.dumps(detail or {})),
    )
    conn.commit()
