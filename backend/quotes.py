"""Quote verification: exact substring match after normalizing whitespace and curly quotes.
Never fuzzy match -- a rule's citation must be a real, findable quote from the policy text.
"""

from __future__ import annotations

import re

_CURLY_SINGLE = {"‘": "'", "’": "'"}
_CURLY_DOUBLE = {"“": '"', "”": '"'}


def normalize(text: str) -> str:
    for curly, straight in {**_CURLY_SINGLE, **_CURLY_DOUBLE}.items():
        text = text.replace(curly, straight)
    return re.sub(r"\s+", " ", text).strip()


def quote_in_text(quote: str, source_text: str) -> bool:
    return normalize(quote) in normalize(source_text)
