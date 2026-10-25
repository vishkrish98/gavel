# Real-use and portability evidence (what moves Gavel toward Tier 3, with no outreach)

1. You are the real reviewer. You ran a $6.5M budget oversight function. Do the manual baseline (evidence/manual_first5_requests.txt) with a stopwatch, honestly, in Excel, as you would do the job. Record minutes and your own errors against the answer key afterward.
2. Real policy portability (optional, 45 minutes, only after the core works): paste the text of ONE real, public university student-government funding policy (for example the funding guidelines a university publishes on its website) into data/private/real_policy.txt (gitignored). Run ONLY the Policy Compiler on it. Report how many rules it compiled, how many quotes verified, and how many you had to correct by hand. Do not publish the policy text in the repo. This shows the idea is not tied to the synthetic policy.
3. Your real-world reflection (6 to 8 sentences, your own words): what happens when reviewers apply a policy inconsistently, and how Gavel's consistency report would have changed a decision you remember. No real names.
4. Label everything honestly: synthetic requests, one expert reviewer, one real policy as a portability check. Do not claim Tier 3 beyond that.

## Task 2 results (completed by Claude at the user's request; policy text not published here)

The real, public funding-policy document of a real university's student union was pasted into
`data/private/real_policy.txt` (gitignored, never committed) and reformatted into
`data/private/real_policy_formatted.txt` (also gitignored) -- 22 real paragraphs covering
equipment purchases, food subsidies, travel, lodging, uniforms/prizes, and coaching compensation.
The real Policy Compiler agent was run against it exactly as it runs against the synthetic policy,
through the live app's own `POST /api/policy` and `POST /api/policy/compile` routes -- no special
code path.

**Compiler results**: of 22 real paragraphs, **21 were reviewed and only 4 became enforceable
rules** (an equipment-purchase documentation threshold, a food-allowance per-person rate, and two
flat-dollar marketing/printing caps). All 4 proposed rules were **quote-verified (4/4, 100%)** --
every quote the compiler cited was an exact substring of the real text. **Zero were corrected by
hand** for this test; the remaining 18 paragraphs were left uncompiled rather than manually
patched, so the numbers above reflect the compiler's unassisted performance on unfamiliar text.

**Simulated run**: six fabricated budget-request lines, modeled on realistic club categories
(academic/professional, athletic, hobby, and special-interest clubs), were run through the full
pipeline against the 4 compiled rules. This surfaced three concrete, real errors, not hypothetical
ones:
1. A travel-mileage reimbursement line was mis-categorized as "supplies" (Gavel's fixed category
   list has no "travel" category) and wrongly reduced by an unrelated $25 cap meant for
   promotional materials.
2. One real policy paragraph packs five distinct numeric sub-rules into a single piece of prose
   (a headline per-person rate, an annual cap, and three narrower per-event/per-day rates for
   different circumstances). The compiler captured only the headline rate, so two otherwise-valid
   food-expense lines were wrongly reduced -- one to $0 -- because the engine applied the wrong
   one of the five numbers.
3. A cash-prize line was allowed in full even though the real policy explicitly prohibits
   subsidizing gifts or awards to members. Gavel's rule schema already supports exactly this kind
   of rule (`prohibited_category`); the compiler simply never recognized that paragraph as one.

**Structural gap, not a bug**: Gavel's rule schema has no way to express a percentage-based
subsidy at all (flat dollar caps only). The real policy is built heavily around percentage
subsidies (travel, championship travel, coaching compensation); none of those real provisions
could ever be enforced by the current schema, even if the compiler recognized every paragraph.

**Honest takeaway**: the idea is portable (the pipeline, the quote-verification, and the human
approval gate all worked unchanged on real text), but the *rule taxonomy* is not -- it was built
around the synthetic policy's specific rule shapes and needs real generalization work (a travel
category, percentage-cap and multi-tier-cap rule types, better per-paragraph decomposition) before
it would reliably catch what this real policy actually requires. This is a genuine limitation, not
a polished success story, and is reported as such in `report.html` Section 8.
