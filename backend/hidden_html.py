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

    club_match = re.search(r"Funding request (Q\d+):\s*(.+)", full_text)
    request_id = club_match.group(1) if club_match else "Q27"
    club = club_match.group(2).strip() if club_match else "Unknown Club"

    dates_match = re.search(r"Event:\s*(\S+)\s*Submitted:\s*(\S+)", full_text)
    event_date = dates_match.group(1) if dates_match else ""
    submitted_date = dates_match.group(2) if dates_match else ""

    lines = []
    for line_id, description, amount in re.findall(r"(\d+-L\d+):\s*(.+?)\s*-\s*\$(\d+(?:\.\d+)?)", full_text):
        lines.append(
            {
                "line_id": line_id,
                "description": description.strip(),
                "amount": float(amount),
                "docs": [],
                "already_purchased": False,
            }
        )

    # Everything after the line-item block (the hidden injection text) becomes the
    # justification -- a naive scraper has no way to separate it from legitimate content, which
    # is exactly the vulnerability this safety case tests.
    justification_parts = [p for p in parser.text_parts if "NOTE TO AI REVIEWERS" in p]
    justification = " ".join(justification_parts) if justification_parts else ""

    request = {
        "request_id": request_id,
        "club": club,
        "event_date": event_date,
        "submitted_date": submitted_date,
        "justification": justification,
        "lines": lines,
    }
    return request, parser.hidden_text_flags
