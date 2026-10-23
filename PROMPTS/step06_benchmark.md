Read CONTEXT.md first. Do Step 6 only: benchmark.py. This is the head-to-head the whole project depends on.

Compare on the 24 requests (158 lines), each model mode run 3 times so we can report the average and the range:
- Mode A, "generic AI assistant": for each request, put the policy and the whole request in ONE gpt-6-luna prompt and ask for a verdict, allowed amount and rule citation for every line, as JSON.
- Mode B, Gavel: Compiler (once), Reader, Skeptic, code Engine.
- Mode C, human baseline: read my hand-filled evidence/manual_first5.csv for Q01 to Q05 (scored with score_manual.py from step 10); report his minutes separately.

For each model mode report: verdict accuracy overall and per verdict type; allowed-dollar error (sum of absolute differences against the key, and total dollars wrongly allowed); lines wrongly ALLOWED that should be denied or reduced (the costly error); lines with a wrong or missing rule citation; citations whose quote is not in the policy (invented evidence); inconsistency across clubs (the same description and facts getting different verdicts); input, cached, output and reasoning tokens; cost; seconds. Break out the hard cases: ambiguous wording (alcohol hidden as "refreshments"), semester cap interactions, needs_docs thresholds, late requests.

Then run these experiments on Mode B and report accuracy and cost for each: (1) Reader with the Skeptic versus without it; (2) stable prompt prefix with the cache breakpoint on versus off (if Portkey does not honor it, report the real cached_tokens we got, which may be zero); (3) reasoning effort low versus medium; (4) parallel versus sequential requests (seconds); (5) compiling the policy once and reusing it versus compiling per request (cost).

Write evidence/benchmark.json and evidence/benchmark.md with clean tables. Report results honestly, including any result where Mode A does as well or better. Do not tune to look good. Stop and report.
