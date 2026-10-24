"""Normalizes a request dict (from JSON body, .txt upload, or .html upload) and inserts it into
the existing database without touching anything else -- unlike backend/load.py's loader, this
never wipes the DB; it's for adding one request at a time via the API (POST /api/requests).
"""

from __future__ import annotations

import sqlite3
import uuid

from backend.hidden_html import parse_hidden_request
from backend.load import _insert_request
from backend.text_request import TextRequestParseError, parse_text_request

REQUIRED_FIELDS = ["club", "event_date", "submitted_date", "justification", "lines"]


class RequestValidationError(ValueError):
    pass


def _assign_ids(request: dict) -> dict:
    request_id = request.get("request_id") or f"UP-{uuid.uuid4().hex[:8]}"
    request = {**request, "request_id": request_id}
    lines = []
    for i, line in enumerate(request["lines"], start=1):
        line_id = line.get("line_id") or f"{request_id}-L{i}"
        lines.append({**line, "line_id": line_id})
    request["lines"] = lines
    return request


def validate_request_dict(request: dict) -> None:
    missing = [f for f in REQUIRED_FIELDS if not request.get(f)]
    if missing:
        raise RequestValidationError(f"Missing required field(s): {', '.join(missing)}.")
    if not isinstance(request["lines"], list) or len(request["lines"]) == 0:
        raise RequestValidationError("`lines` must be a non-empty list.")
    for i, line in enumerate(request["lines"], start=1):
        if "description" not in line or "amount" not in line:
            raise RequestValidationError(f"Line {i} is missing `description` or `amount`.")


def parse_uploaded_request(filename: str, content: bytes) -> dict:
    """Dispatches on file extension. Raises RequestValidationError with a clear message on
    anything that doesn't parse."""
    lower = filename.lower()
    try:
        if lower.endswith(".json"):
            import json

            request = json.loads(content.decode("utf-8"))
        elif lower.endswith(".html") or lower.endswith(".htm"):
            import tempfile
            from pathlib import Path

            with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
                tmp.write(content)
                tmp_path = Path(tmp.name)
            try:
                request, hidden_flags = parse_hidden_request(tmp_path)
                request["_hidden_flags"] = hidden_flags
            finally:
                tmp_path.unlink(missing_ok=True)
        elif lower.endswith(".txt"):
            request = parse_text_request(content.decode("utf-8"))
        else:
            raise RequestValidationError(f"Unsupported file type for {filename!r}: expected .txt, .html, or .json.")
    except (ValueError, UnicodeDecodeError) as exc:
        raise RequestValidationError(f"Could not parse {filename!r}: {exc}") from exc

    validate_request_dict(request)
    return request


def insert_request(conn: sqlite3.Connection, request: dict, source: str) -> tuple[str, int]:
    """Assigns ids if missing, validates, inserts. Returns (request_id, line_count). Raises
    RequestValidationError (caller should turn that into a 400) if the id already exists or the
    shape is invalid."""
    validate_request_dict(request)
    request = _assign_ids(request)
    existing = conn.execute("SELECT 1 FROM requests WHERE id = ?", (request["request_id"],)).fetchone()
    if existing:
        raise RequestValidationError(f"A request with id {request['request_id']!r} already exists.")

    hidden_flags = request.pop("_hidden_flags", None)
    line_count = _insert_request(conn, request, source=source)
    if hidden_flags:
        for flag in hidden_flags:
            conn.execute(
                "INSERT INTO hidden_text_flags (request_id, tag, reason, text) VALUES (?, ?, ?, ?)",
                (request["request_id"], flag["tag"], flag["reason"], flag["text"]),
            )
    conn.commit()
    return request["request_id"], line_count
