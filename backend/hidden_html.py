"""Parses data/safety_request_hidden.html (request Q27) the way a naive scraper would: pull ALL
text including hidden text, because the hidden text IS the injection attack we want downstream
agents and defenses to be tested against. Separately records which elements were hidden (font-size
0 or white-on-white) as `hidden_text_flags` -- the safety step (step07) uses those flags, but this
loader does not strip or special-case the text itself.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path


def _is_zero_font_size(style: str) -> bool:
    return bool(re.search(r"font-size\s*:\s*0(?:px|pt|em|%)?\b", style, re.IGNORECASE))


def _is_white_on_white(style: str) -> bool:
    colors = re.findall(r"(?:^|;)\s*color\s*:\s*([^;]+)", style, re.IGNORECASE)
    backgrounds = re.findall(r"(?:^|;)\s*background(?:-color)?\s*:\s*([^;]+)", style, re.IGNORECASE)

    def _is_white(value: str) -> bool:
        value = value.strip().lower()
        return value in {"#fff", "#ffffff", "white", "rgb(255,255,255)", "rgb(255, 255, 255)"}

    return any(_is_white(c) for c in colors) and any(_is_white(b) for b in backgrounds)


class _HiddenAwareParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.text_parts: list[str] = []
        self.hidden_text_flags: list[dict[str, str]] = []
        self._style_stack: list[tuple[str, str]] = []  # (tag, style)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        style = next((v or "" for k, v in attrs if k == "style"), "")
        self._style_stack.append((tag, style))

    def handle_endtag(self, tag: str) -> None:
        if self._style_stack and self._style_stack[-1][0] == tag:
            self._style_stack.pop()

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if not text:
            return
        # <title> is page metadata (what a browser tab shows), not body content -- a naive
        # scraper extracting "the request" would target the body, not the <head>. Skipping it
        # also keeps this parser generic (step08a reuses it for arbitrary HTML uploads, not just
        # Q27's one fixture, where leaking <title> text into the justification would be noise).
        if any(tag == "title" for tag, _ in self._style_stack):
            return
        self.text_parts.append(text)
        if self._style_stack:
            tag, style = self._style_stack[-1]
            if _is_zero_font_size(style):
                self.hidden_text_flags.append({"tag": tag, "reason": "font-size:0", "text": text})
            elif _is_white_on_white(style):
                self.hidden_text_flags.append({"tag": tag, "reason": "white-on-white", "text": text})


def parse_hidden_request(path: Path) -> tuple[dict, list[dict[str, str]]]:
    """Returns (request_dict shaped like requests_input.json entries, hidden_text_flags)."""
    html_text = path.read_text()
    parser = _HiddenAwareParser()
    parser.feed(html_text)
    full_text = "\n".join(parser.text_parts)

    # Generalized beyond Q27's own "Q\d+" id so this same parser also serves POST /api/requests'
    # general-purpose HTML uploads (step08a) -- any non-whitespace token works as the request id.
    club_match = re.search(r"Funding request (\S+):\s*(.+)", full_text)
    request_id = club_match.group(1) if club_match else None
    club = club_match.group(2).strip() if club_match else "Unknown Club"

    dates_match = re.search(r"Event:\s*(\S+)\s*Submitted:\s*(\S+)", full_text)
    event_date = dates_match.group(1) if dates_match else ""
    submitted_date = dates_match.group(2) if dates_match else ""

    line_pattern = re.compile(r"^(\S+):\s*(.+?)\s*-\s*\$(\d+(?:\.\d+)?)$")
    lines = []
    for part in parser.text_parts:
        line_match = line_pattern.match(part)
        if line_match:
            line_id, description, amount = line_match.groups()
            lines.append(
                {
                    "line_id": line_id,
                    "description": description.strip(),
                    "amount": float(amount),
                    "docs": [],
                    "already_purchased": False,
                }
            )

    # Everything that isn't the title, the dates, or a line item becomes the justification -- for
    # Q27 that's exactly the two hidden spans (a naive scraper has no way to separate them from
    # legitimate content, which is exactly the vulnerability this safety case tests); for a
    # general upload, it's whatever other text the submitter wrote.
    title_text = club_match.group(0) if club_match else None
    dates_text = dates_match.group(0) if dates_match else None
    justification_parts = [
        p for p in parser.text_parts if p != title_text and p != dates_text and not line_pattern.match(p)
    ]
    justification = " ".join(justification_parts).strip()

    request = {
        "request_id": request_id,
        "club": club,
        "event_date": event_date,
        "submitted_date": submitted_date,
        "justification": justification,
        "lines": lines,
    }
    return request, parser.hidden_text_flags
