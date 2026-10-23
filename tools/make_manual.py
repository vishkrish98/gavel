import json, sys
R = json.load(open(sys.argv[1] + "/requests_input.json"))[:5]
with open(sys.argv[2] + "/manual_first5_requests.txt", "w") as f:
    f.write("MANUAL BASELINE: requests Q01 to Q05. Open data/policy_synthetic.txt. For EVERY line item decide: allowed, reduced (capped; give the allowed dollar amount), denied, or needs_docs (held until documents are provided), and cite the rule paragraph. Use Excel and nothing else. Do NOT open the answer key or any app output. Start a stopwatch for all five requests.\n\n")
    for r in R:
        f.write(f"=== {r['request_id']} {r['club']}  event {r['event_date']}  submitted {r['submitted_date']} ===\n{r['justification']}\n")
        for l in r["lines"]: f.write(f"  {l['line_id']}: {l['description']}  ${l['amount']}  docs={l['docs'] or 'none'}  already_purchased={l['already_purchased']}\n")
        f.write("\n")
open(sys.argv[2] + "/manual_first5_TEMPLATE.csv", "w").write("request_id,line_id,verdict,allowed_amount,rule_para\n")
