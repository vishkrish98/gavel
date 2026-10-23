Read CONTEXT.md first. Do Step 3 only: the deterministic layer, with NO model calls in this step.

1. Load the 12 true rules from data/policy_rules_truth.json as approved rules (a test fixture, labeled as such). Feed the TRUE line facts from data/requests_truth.json (category, headcount, quantity, nights, unit cost) into run_engine and compare every line's verdict and allowed amount with the key. Expected: 158 of 158 lines match on verdict and amount (tools/make_funding_data.py already computes them; the app's engine must reproduce it).
2. Run allocate with the true allowed totals and compare with data/optimizer_truth.json for all four scenarios. Expected: exact match to the cent.
3. Report consistency_report on data/prior_decisions.json: expected 6 of 30 inconsistent.
4. Save evidence/engine_eval.json. Report tokens used (zero, and say so). Update harness.md. Stop and report.
