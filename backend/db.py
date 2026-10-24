"""SQLite schema for Gavel. The database is created automatically on first run at
data/gavel.db (gitignored — data/*.db). Nothing here ever updates or deletes a row in `audit`;
that table is append-only by construction (insert-only statements, no update/delete code path).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "gavel.db"

SCHEMA = """
CREATE TABLE policy_paragraphs (
    para_id TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    kind TEXT
);

CREATE TABLE rules (
    id TEXT PRIMARY KEY,
    para_id TEXT NOT NULL,
    type TEXT NOT NULL,
    params_json TEXT NOT NULL,
    quote TEXT NOT NULL,
    quote_verified INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'proposed' CHECK (status IN ('proposed', 'approved', 'rejected')),
    approved_by TEXT
);

CREATE TABLE requests (
    id TEXT PRIMARY KEY,
    club TEXT NOT NULL,
    event_date TEXT NOT NULL,
    submitted_date TEXT NOT NULL,
    justification TEXT NOT NULL,
    source TEXT NOT NULL
);

CREATE TABLE lines (
    id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL REFERENCES requests(id),
    description TEXT NOT NULL,
    amount REAL NOT NULL,
    docs_json TEXT NOT NULL DEFAULT '[]',
    already_purchased INTEGER NOT NULL DEFAULT 0,
    category TEXT,
    headcount INTEGER,
    qty INTEGER,
    nights INTEGER,
    unit_cost REAL,
    quarantined INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE verdicts (
    run_id TEXT NOT NULL,
    line_id TEXT NOT NULL REFERENCES lines(id),
    verdict TEXT NOT NULL,
    allowed_amount REAL NOT NULL,
    rules_json TEXT NOT NULL DEFAULT '[]',
    explanation TEXT,
    flagged_for_review INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (run_id, line_id)
);

CREATE TABLE runs (
    id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL DEFAULT 'running',
    mode TEXT
);

CREATE TABLE allocations (
    run_id TEXT NOT NULL,
    scenario TEXT NOT NULL,
    club TEXT NOT NULL,
    amount REAL NOT NULL
);

-- requested/approved only (no `inconsistent` or `policy_allowed` -- those are answer-key fields
-- in data/prior_decisions.json and must not be loaded; see PROMPTS/step01_data_layer.md #2).
-- docs_json and term are kept as extra, non-answer-key context so step03's consistency check can
-- re-derive what the policy would allow without re-reading the raw JSON file.
CREATE TABLE prior_decisions (
    id TEXT PRIMARY KEY,
    club TEXT NOT NULL,
    description TEXT NOT NULL,
    requested REAL NOT NULL,
    approved REAL NOT NULL,
    docs_json TEXT NOT NULL DEFAULT '[]',
    term TEXT
);

CREATE TABLE usage (
    run_id TEXT NOT NULL,
    agent TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    cached_tokens INTEGER NOT NULL DEFAULT 0,
    cache_write_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL,
    reasoning_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL,
    seconds REAL NOT NULL,
    cost_usd REAL NOT NULL,
    created_at TEXT NOT NULL
);

-- Append-only: only INSERT statements should ever touch this table anywhere in the codebase.
CREATE TABLE audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT,
    ts TEXT NOT NULL,
    event TEXT NOT NULL,
    detail_json TEXT NOT NULL DEFAULT '{}'
);

-- Added in step04 (not in the step01 schema list): the Drafter's output has nowhere else to
-- live. 'status' starts at 'awaiting_approval' and only a human approval click (wired up in a
-- later step's backend route) can move it to 'approved' -- nothing here is exported on its own.
CREATE TABLE drafts (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    request_id TEXT,
    kind TEXT NOT NULL CHECK (kind IN ('questions', 'memo')),
    content_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'awaiting_approval' CHECK (status IN ('awaiting_approval', 'approved')),
    created_at TEXT NOT NULL
);

-- Added in step07: the canonical record of hidden text found at ingestion (font-size:0,
-- white-on-white, etc. -- see backend/hidden_html.py). backend/safety.py reads this table to know
-- what to strip from a request's justification before it reaches a model; not hardcoded to one
-- filename, so it generalizes if another hidden-HTML request is ever loaded.
CREATE TABLE hidden_text_flags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT NOT NULL,
    tag TEXT NOT NULL,
    reason TEXT NOT NULL,
    text TEXT NOT NULL
);
"""


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection, *, fresh: bool = True) -> None:
    """Create all tables. With fresh=True (the loader's default), drops any existing tables
    first so re-running the loader always produces a clean, reproducible database."""
    if fresh:
        # Drop with FK enforcement off: tables reference each other (lines -> requests,
        # verdicts -> lines) and sqlite's FK pragma blocks dropping a referenced table out of
        # dependency order even though the whole schema is about to be recreated anyway.
        conn.execute("PRAGMA foreign_keys = OFF")
        tables = [
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            if not row[0].startswith("sqlite_")
        ]
        for table in tables:
            conn.execute(f"DROP TABLE IF EXISTS {table}")
        conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    conn.commit()
