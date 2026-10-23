Read CONTEXT.md first. Do Step 2 only: the MCP server in mcp_server/server.py (FastMCP, stdio), using the HW5 server as the pattern.

Implement these tools, all deterministic (no model calls):
- load_policy(), list_rules(status): policy paragraphs and rules.
- propose_rule(para_id, type, params, quote): stores a proposed rule and runs verify_quote on the quote against that paragraph in the same call; a quote that does not verify is stored as rejected with reason quote_not_found and an audit entry.
- approve_rule(rule_id, by): the human approval step; only approved rules are used by the engine.
- verify_quote(text_id, quote): True only if the quote appears as an exact substring after normalizing whitespace and curly quotes. Never fuzzy match.
- get_request(request_id).
- check_line(request_id, line_id): applies the APPROVED rules to one line with its extracted facts (category, headcount, quantity, nights, unit cost) in the order used by tools/make_funding_data.py eval_line, and returns verdict, allowed amount and rule ids. The semester cap is applied across a request's lines in order.
- run_engine(request_id): runs check_line over all lines; explain_line(line_id): returns the verdict with the exact policy quote for each rule hit.
- consistency_report(): compares prior_decisions with what the engine allows for the same category and facts and returns inconsistent decisions and an inconsistency rate.
- allocate(pot, alpha): the water-filling optimizer from tools/make_funding_data.py (weights allowed*(1-alpha+alpha*utilization), capped at each club's allowed amount).
- log_usage(...): writes a usage row and computes cost from the pricing config.

Register the server in .mcp.json, write tests/test_mcp.py that calls every tool with real data and asserts the results, and write output/mcp_smoke.json with each tool call and its real result, including a verified quote and a fake quote being rejected. State honestly in that file how the calls were made. Update harness.md with the tool list. Stop and report.
