# Gavel benchmark: Mode A (generic assistant) vs. Mode B (Gavel) vs. Mode C (human)

24 real requests, 158 lines. Each of Mode A and Mode B run 3 times (fresh data each time); numbers below are average (min-max) across those 3 runs unless noted. Reported honestly -- including anywhere Mode A does as well or better.

## Headline comparison

| Metric | Mode A (generic) | Mode B (Gavel) |
| --- | --- | --- |
| Overall verdict accuracy | 0.981 (0.981-0.981) | 1.000 (1.000-1.000) |
| Sum |allowed-dollar error| | $9500.00 ($9500.00-$9500.00) | $0.00 ($0.00-$0.00) |
| Total $ wrongly allowed (overpayment) | $9500.00 | $0.00 |
| Avg cost per run (24 requests) | $0.0095 | $0.0147 |
| Avg tokens per run | 43559 | 96617 |
| Avg wall-clock seconds per run | 4.2 | 24.3 |

## Verdict accuracy per type (rep 1 of 3, representative)

| Verdict type | Mode A | Mode B |
| --- | --- | --- |
| allowed | 1.000 | 1.000 |
| denied | 1.000 | 1.000 |
| needs_docs | 0.846 | 1.000 |
| reduced | 0.952 | 1.000 |

## Citations (rep 1 of 3)

| | Mode A | Mode B |
| --- | --- | --- |
| correct | 79 | 158 |
| missing | 0 | 0 |
| wrong real quote | 79 | 0 |
| invented not in policy | 0 | 0 |

> Mode B only ever cites a rule when the engine actually applied it, matching the answer key's convention exactly. Mode A sometimes cites a real, relevant policy sentence for a line that didn't actually hit any limit (e.g. showing the $15/person food cap on an allowed line under that cap) -- scored here as `wrong_real_quote` since the answer key only records a citation when a rule fired, but it's better described as Mode A being more talkative/explanatory than wrong or dishonest.

## Cross-club consistency (rep 1 of 3): identical description+amount+docs, different clubs

| | Mode A | Mode B |
| --- | --- | --- |
| Groups checked | 30 | 30 |
| Inconsistent groups | 7 | 7 |
| Inconsistency rate | 0.233 | 0.233 |

> A "group" is a set of lines with identical description, amount, docs, and already-purchased flag across different clubs -- same facts, so a non-inconsistent reviewer should reach the same verdict and dollar amount. Mode B's groups can still legitimately diverge when each club's own semester cap trims a different amount; that is correct policy behavior, not inconsistency, and is not separated out below.

## Hard cases (rep 1 of 3): verdict accuracy by scenario

| Scenario | n | Mode A | Mode B |
| --- | --- | --- | --- |
| ambiguous wording alcohol or gift card | 8 | 1.000 | 1.000 |
| semester cap interactions | 0 | n/a | n/a |
| needs docs threshold | 13 | 0.846 | 1.000 |
| late requests deadline | 19 | 1.000 | 1.000 |

## Mode C: human baseline

See evidence/manual_first5.csv and step10's score_manual.py for scoring.

## Experiments on Mode B

### 1. Reader with Skeptic vs. without

With Skeptic: 46 calls, $0.014665. Without: 25 calls, $0.009734.

Lines flagged: 8 (0 were real misclassifications, 8 were not).

> Verdict/category accuracy is identical with or without the Skeptic by construction -- it never changes a category or verdict, only flags lines for human review. The only real difference is cost/tokens (its own calls) and how many of its flags were real Reader errors vs. reasonable-but-unnecessary caution.

### 2. Stable prompt prefix (cache) vs. broken prefix

Sample: 6 requests each. Stable-prefix mean cached_tokens: 0. Broken-prefix mean cached_tokens: 0.

> cached_tokens is the real value PydanticAI's usage.cache_read_tokens returns from the provider -- not estimated. If Portkey doesn't honor caching for this model, both conditions may show 0; that's reported as-is, not papered over.

### 3. Reasoning effort low vs. medium (Request Reader, category accuracy)

| Effort | Category accuracy | Tokens | Cost |
| --- | --- | --- | --- |
| low | 1.000 | 14201 | $0.002212 |
| medium | 1.000 | 14524 | $0.002374 |

### 4. Parallel vs. sequential requests (wall-clock seconds)

Sample: 8 requests. Parallel: 0.57s. Sequential: 1.58s. Speedup: 2.76x.

### 5. Compile policy once vs. per request (cost, projected)

One real compile: $0.000899. Projected if compiled once per request (24 requests): $0.021574 (24.0x more expensive).

