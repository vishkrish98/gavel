# Can the Skeptic catch a real error? A stress test (2026-10-26)

Every run in this project so far (the final pipeline run, all three benchmark repetitions) has
scored 100% on category and verdict accuracy, which means the Skeptic has never had a real error
to find: across the whole project, 8 lines were flagged and 0 of them were actual
Request Reader misclassifications (`evidence/run_check.json` → `skeptic`). That's an honest gap,
not a hidden one -- see `report.html` Section 8. This stress test asks the question directly: is
the mechanism capable of working at all, or is it just never getting a real chance?

**What this is, honestly**: a deliberately engineered adversarial test, not a naturally occurring
example from the synthetic dataset. Every request below says so in its own `justification` field.
All real model calls against the live app; none of these numbers are invented or estimated.

## Round 1: six real adversarial attempts, 16 lines, real model calls

Six different attack strategies against the Request Reader, run for real:

| # | Strategy | Example line | Result |
| --- | --- | --- | --- |
| 1 | Alcohol/gift-card disguised as food/prize | "champagne, sparkling cider... for the banquet" | Correctly tagged `alcohol`, denied |
| 1 | | "Digital gift certificates awarded as raffle prizes" | Correctly tagged `gift_card`, denied |
| 2 | Obscure quantity words, bulk-unit math | "a dozen attendees" (12), "a gross of them" (144), "3 boxes of 24 bars... $1 per bar" (72) | All correctly computed |
| 3 | Narrative ambiguity (resolvable with care) | "3 pizzas arrived... drinks for all 60 students" | Correctly used 60; **flagged anyway** for a real inconsistency (amount doesn't plausibly cover 3 pizzas) |
| 4 | Implicit category cues, reverse traps | "happy hour and bar snacks" (no literal "alcohol") | Correctly tagged `alcohol` |
| 4 | | "a keg of root beer floats" (contains the word "beer," is not alcohol) | Correctly stayed `food`, not fooled by the word |
| 4 | | "Appreciation tokens... redeemable at the campus bookstore" | Correctly tagged `gift_card` despite the euphemism |
| 5 | Conflicting headcounts, resolvable | "contracted... 40... even though only 20 actually showed up" | Correctly used the contracted/paid basis (40), not attendance |

Sixteen lines, sixteen correct classifications. Two lines were flagged by the Skeptic for genuine
price-plausibility reasons (a bulk-water unit-cost mismatch, and the pizza-reimbursement
inconsistency above) -- real, substantive flags, but neither traces to a Reader classification
error, since the Reader's own extraction was correct in both cases. Full real output, every
request and run ID: `evidence/skeptic_stress_test.json`.

## Round 2: a genuinely self-contradictory line, 15 real repetitions

Round 1's resolvable traps kept getting resolved correctly, so round 2 removed the resolving
information entirely: a line with two flatly conflicting headcounts and no narrative cue for
which one is real --

> "Catering for the mixer. Headcount: 15. Total: $350. Final attendee count: 35."

There is no objectively correct answer here; a careful human would ask the club to clarify, which
is exactly the outcome worth testing for. Ran this exact line 15 times (real model calls, two
batches, `evidence/skeptic_stress_test_reps.json`):

| Outcome | Count | What happened |
| --- | --- | --- |
| Reader uses headcount 15 → per_person_cap reduces the line to $225 | 12 of 15 | The line's engine-preliminary verdict is `reduced`, not `allowed` -- so by the architecture's own design (the Skeptic only reviews lines the engine would currently allow in full), **the Skeptic never gets a chance to review it at all** |
| Reader uses headcount 35 → fully allowed at $350, **and the Skeptic flags it** | 3 of 15 (20%) | Real flags, e.g. `run-45caf0ac`: *"Description gives conflicting headcounts (15 and final count 35); confirm the correct quantity for the $350 catering charge."* |

**The honest finding, in both directions**: the Skeptic mechanism does work -- on 3 of 15 real
runs, it correctly identified a genuinely self-contradictory input and flagged it for a human to
resolve, rather than silently picking a number and hiding the ambiguity. But it is not reliable on
this input, and the reason is architectural, not a model failure: this pipeline only sends
*already-allowed* lines to the Skeptic. When the same contradiction happens to resolve toward the
smaller number, the per-person cap mechanically reduces the line before the Skeptic ever sees it --
no flag, no human review, just a quietly reduced amount. The one thing that never changes either
way: the Engine's math is correct for whichever headcount the Reader reports, so no dollar amount
is ever wrong relative to the (possibly wrong) extracted facts -- the risk here is entirely about
*which ambiguous reading gets used*, not about the arithmetic on top of it.

## What this means for the report

- The existing "0/8 real errors, Skeptic's value unproven" framing (`report.html` Section 8)
  stays accurate for the graded, synthetic dataset -- nothing here changes those numbers.
- This stress test adds a genuine, reproducible data point the formal benchmark can't:
  evidence that the Skeptic *can* work, under the right (adversarial, engineered) conditions, 20%
  of the time on a truly ambiguous input.
- It also surfaces a real, previously undocumented limitation: the Skeptic's review only applies
  to lines the engine would currently allow in full, so an ambiguity that happens to resolve toward
  a *lower* number can be mechanically reduced without any human ever being alerted that the
  underlying data was contradictory in the first place.
