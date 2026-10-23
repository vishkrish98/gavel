"""Single source of truth for gpt-6-luna pricing (CONTEXT.md hard rule: "Keep prices in ONE
config file"). Only this file should contain dollar-per-token figures.
"""

from __future__ import annotations

MODEL_NAME = "gpt-6-luna"

# Dollars per 1,000,000 tokens, gpt-6-luna via Portkey.
# Source: MGT 409 Lecture 11 pricing table. As of: 2026-10-23 (the date this file was last
# checked against that table). If the course updates the table, update these four numbers and
# this date -- nothing else in the codebase hardcodes a price (CONTEXT.md: "Keep prices in ONE
# config file").
PRICE_PER_MILLION = {
    "input": 0.10,
    "cached": 0.01,
    "cache_write": 0.125,
    "output": 0.50,
}


def compute_cost_usd(
    input_tokens: int,
    cached_tokens: int,
    cache_write_tokens: int,
    output_tokens: int,
) -> float:
    """Cost per call = ((input - cached - cache_write) * price_input + cached * price_cached
    + cache_write * price_cache_write + output * price_output) / 1,000,000."""
    billed_input = max(input_tokens - cached_tokens - cache_write_tokens, 0)
    cost = (
        billed_input * PRICE_PER_MILLION["input"]
        + cached_tokens * PRICE_PER_MILLION["cached"]
        + cache_write_tokens * PRICE_PER_MILLION["cache_write"]
        + output_tokens * PRICE_PER_MILLION["output"]
    ) / 1_000_000
    return round(cost, 8)
