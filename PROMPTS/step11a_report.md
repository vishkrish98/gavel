Read CONTEXT.md first. Build report.html in the repo root: one self-contained HTML file (all CSS inline, all images embedded as base64, no external requests) that prints to 10 to 15 pages on US Letter.

STRUCTURE, in this order: 1 Title and links (Gavel, Vish Gopalakrishnan, the GitHub repo URL, one sentence on the app); 2 Motivation; 3 What is new; 4 The agents; 5 Tokenomics; 6 Safety; 7 Impact; 8 Limits and next steps.

RULES
- Every number comes from files in evidence/ and output/ (start from evidence/numbers.md). Never invent or round up a figure. If a number is missing, write [[MISSING: what is needed]] in a visible highlight.
- Anything only I can supply (my motivation paragraph, my stopwatch minutes and Excel errors, the real-world reflection, competitor descriptions and links, screenshots not yet in report_assets/) goes in as a highlighted [[USER: what to paste here]] placeholder; list all placeholders at the end of your reply.
- Section 2: who does funding review (student governments, committees), what goes wrong (inconsistent application, hidden violations, slow review), and the headline question: is this better than a reviewer with Excel and a generic AI assistant?
- Section 3: name real competitors I supply (for example CampusGroups, Campus Labs, homegrown tools) and contrast: they collect requests and track budgets; Gavel compiles policy into approved, quote-verified rules and checks every line with code.
- Section 4 includes an inline SVG diagram: Chair on top; Policy Compiler, Request Reader (marked parallel), Skeptic, Engine (code), Optimizer (code) and Drafter below; the MCP tools row beneath; the human approval gates (rules, memo). Add one traced real run from output/trace_run1.json as a numbered step list with the matching screenshots.
- Section 5 includes the real token table, the cost model with its assumptions, the Mode A vs Mode B table, and a small inline-SVG bar chart of tokens by agent.
- Section 6 includes the before and after safety table, the false-positive control (Q26), and the screenshots.
- Section 7 includes the head-to-head (Excel vs generic AI vs Gavel) on accuracy, dollars wrongly allowed, consistency and time, the consistency finding on prior decisions, and the scenario results. Label the human baseline as one expert reviewer on five requests.
- Be honest: report results where Gavel was not better, and say all requests are synthetic.
- Design: clean and readable; serif headings, sans body, one accent colour; figures with captions, @page margins, no orphan headings, page-break rules for figures.
- Verify the page count by printing to PDF with a headless browser if available and report it; if not, say so.
Stop and report the page count and the placeholder list.
