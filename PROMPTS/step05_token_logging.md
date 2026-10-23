Read CONTEXT.md first. Do Step 5 only: token logging and cost.

1. Wrap every model call so each one writes a usage row: agent, run id, input_tokens, cached_tokens, cache_write_tokens, output_tokens, reasoning_tokens, total_tokens, seconds, cost_usd. Inspect the real response fields first (print one raw response) and log exactly what the provider returns. Do not estimate.
2. Put prices in backend/pricing.py with an as-of date and a comment citing the course Lecture 11 table: gpt-6-luna input 0.10, cached 0.01, cache write 0.125, output 0.50 per 1M tokens. Use the cost formula from CONTEXT.md.
3. API routes: GET /api/usage?run_id= (totals per agent and per run) and GET /api/runs.
4. backend/projection.py turns measured data into: cost to compile one policy (once per policy), cost per request, cost per line item, and a semester cost for: one student government with 24 clubs, one with 150 clubs (assumption labeled), and a platform serving 1,000 institutions (assumption labeled). Add the human comparison: reviewer hours per request at an assumed 20 minutes and an assumed hourly rate, labeled as assumptions you can change. Put every assumption in one clearly labeled config block. Output a table to evidence/cost_model.md.
5. Run the pipeline once and show the real usage table and the projection. Update harness.md. Stop and report.
