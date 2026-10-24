"""Parses a plain-text funding request upload (POST /api/requests, .txt format).

No standard plain-text request format exists anywhere in this kit, so this defines the simplest
one that covers the same fields as the JSON/HTML formats (see backend/hidden_html.py for the HTML
side). Documented here, in harness.md, and in the route's own error message so a newcomer gets a
clear format reminder on a parse failure:

    Club: <name>
    Event: YYYY-MM-DD
    Submitted: YYYY-MM-DD
    Justification: <free text>
    Lines:
    - <description> - $<amount>
    - <description> - $<amount> [docs: quotes3,contract]
    - <description> - $<amount> [already_purchased]
"""

from __future__ import annotations

import re

FORMAT_HELP = (
    "Expected plain-text format:\n"
    "Club: <name>\n"
    "Event: YYYY-MM-DD\n"
    "Submitted: YYYY-MM-DD\n"
    "Justification: <free text>\n"
    "Lines:\n"
    "- <description> - $<amount>\n"
    "- <description> - $<amount> [docs: quotes3,contract]\n"
    "- <description> - $<amount> [already_purchased]"
)


class TextRequestParseError(ValueError):
    pass


def parse_text_request(text: str) -> dict:
    club_match = re.search(r"^Club:\s*(.+)$", text, re.MULTILINE)
    event_match = re.search(r"^Event:\s*(\S+)", text, re.MULTILINE)
    submitted_match = re.search(r"^Submitted:\s*(\S+)", text, re.MULTILINE)
    justification_match = re.search(r"^Justification:\s*(.+?)(?=^Lines:)", text, re.MULTILINE | re.DOTALL)
    lines_block_match = re.search(r"^Lines:\s*(.+)$", text, re.MULTILINE | re.DOTALL)

    missing = [
        name
        for name, match in [("Club", club_match), ("Event", event_match), ("Submitted", submitted_match), ("Justification", justification_match), ("Lines", lines_block_match)]
        if match is None
    ]
    if missing:
        raise TextRequestParseError(f"Missing or unparseable field(s): {', '.join(missing)}.\n\n{FORMAT_HELP}")

    lines = []
    for i, raw_line in enumerate(lines_block_match.group(1).strip().splitlines(), start=1):
        raw_line = raw_line.strip()
        if not raw_line or not raw_line.startswith("-"):
            continue
        content = raw_line[1:].strip()
        line_match = re.match(r"^(.+?)\s*-\s*\$(\d+(?:\.\d+)?)\s*(\[.*\])?$", content)
        if not line_match:
            raise TextRequestParseError(
                f"Could not parse line {i}: {raw_line!r}\n\n{FORMAT_HELP}"
            )
        description, amount_str, tags = line_match.groups()
        tags = tags or ""
        docs_match = re.search(r"docs:\s*([\w,]+)", tags)
        docs = [d.strip() for d in docs_match.group(1).split(",")] if docs_match else []
        already_purchased = "already_purchased" in tags
        lines.append(
            {
                "line_id": None,  # assigned by the caller once the request_id is known
                "description": description.strip(),
                "amount": float(amount_str),
                "docs": docs,
                "already_purchased": already_purchased,
            }
        )

    if not lines:
        raise TextRequestParseError(f"No line items found under 'Lines:'.\n\n{FORMAT_HELP}")

    return {
        "request_id": None,  # assigned by the caller
        "club": club_match.group(1).strip(),
        "event_date": event_match.group(1).strip(),
        "submitted_date": submitted_match.group(1).strip(),
        "justification": justification_match.group(1).strip(),
        "lines": lines,
    }
