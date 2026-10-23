# Gavel cost model

Built from real measured usage for run `run1` (61 model calls, 103,784 tokens, $0.0160 total, 158 lines scored). No token count here is estimated -- every number comes from the `usage` table, written once per real model call from the provider's own response fields.

## Assumptions (change these to re-run)

| Assumption | Value | Status |
| --- | --- | --- |
| Clubs in this project's dataset | 24 | measured |
| Clubs, larger student government | 150 | **assumption** |
| Institutions on a shared platform | 1000 | **assumption** |
| Requests per club per semester | 1 | **assumption** |
| Clubs per platform institution | 24 | **assumption** |
| Reviewer minutes per request (manual) | 20 | **assumption** |
| Reviewer hourly rate (USD) | 20.0 | **assumption** |

## Unit costs (measured, from run above)

| Unit | Cost (USD) |
| --- | --- |
| Compile one policy (once per semester) | $0.000751 |
| One whole-pot decision memo (once per semester) | $0.000124 |
| Per request (Reader + Skeptic + drafted questions) | $0.000632 |
| Per line item | $0.000096 |

## Semester cost projections (USD)

| Scenario | Total cost | Status |
| --- | --- | --- |
| 24 clubs measured | $0.0160 | measured |
| 150 clubs assumption | $0.0956 | **assumption** |
| platform 1000 institutions assumption | $16.0400 | **assumption** |

## Human comparison (assumption-labeled)

Assumed 20 minutes/request at $20.00/hour = **$6.67/request** for one manual review.

| Scale | Human reviewer cost | Gavel pipeline cost | Status |
| --- | --- | --- | --- |
| 24 requests (measured scale) | $160.00 | $0.0152 | measured scale, assumed rate |
| 150 requests | $1,000.00 | $0.0948 | **assumption** |

> This compares the AI pipeline's per-request cost to the cost of one committee member's manual review time at the assumed rate. It is NOT a claim that Gavel replaces that review -- the committee still makes every decision (CONTEXT.md hard rule 10). The honest comparison is the cost of Gavel's first-pass packet (rule citations, verdicts, flagged lines, drafted questions) against the cost of a human producing the same thing from scratch.

## Per-agent breakdown (measured)

| Agent | Cost (USD) | Tokens |
| --- | --- | --- |
| policy_compiler | $0.000751 | 5,311 |
| request_reader | $0.008775 | 55,327 |
| skeptic | $0.004733 | 34,033 |
| drafter_questions | $0.001655 | 8,569 |
| drafter_memo | $0.000124 | 544 |
