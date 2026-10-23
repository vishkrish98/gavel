Read CONTEXT.md first. Do Step 8b only: the React + Vite + TypeScript UI. Reuse the HW5 dashboard's design tokens and components where it helps: dark, scholarly, modern (serif headings, clean sans body, a gavel-brass accent). Look and feel is graded for a newcomer: clean layout, clear controls, nothing confusing. It should look like a tool a student-government treasurer would trust.

Screens and parts:
1. Start: a big "Try the sample" button (loads the demo, then walks the user through: review rules, approve, run), plus paste and upload for your own policy and requests, with a short plain-language hint under each.
2. Rules: the compiled rules as cards, each with the exact policy quote highlighted, a Verified badge, and Approve or Reject. An "Approve all verified" button. Decoy paragraphs shown as "not a rule" with why.
3. Run view: the agents as nameplates (Chair, Policy Compiler, Request Reader, Skeptic, Engine, Optimizer, Drafter) with live status (waiting, working, done), a progress bar, and a live event feed showing tool calls as a readable trace (a glass box).
4. Review table: all requests and lines with verdict chips (allowed, reduced, denied, needs documents), filters, and search; clicking a line opens a side panel with the description, extracted facts, the rule hit, the exact policy quote highlighted, the allowed amount and the reason. Skeptic flags shown as "review this".
5. Scenarios: sliders for the pot size and the weight on past utilization (alpha); an instant bar chart of each club's allocation versus its policy-allowed amount, computed in code on every slider move, with a plain sentence explaining the trade-off. A table of who gains and loses between two settings.
6. Consistency: last year's decisions that disagree with the policy, with the dollar gap and the inconsistency rate.
7. A banner when an injection was blocked, with where it was and what it said.
8. Cost panel: tokens (input, cached, output) and dollars for the run, from /api/usage.
9. Drafts: committee questions and the decision memo, labeled DRAFT until the committee approves; Download CSV.
Include empty states, loading states, friendly errors, keyboard focus styles. Layout must work at a laptop width and degrade sensibly narrower.

BUILD: compile the frontend and commit the built frontend/dist so a fresh clone needs no Node. run.py serves frontend/dist and only rebuilds if Node is present and dist is missing. Update .gitignore so dist is tracked. Show screenshots of each screen from a real run. Stop and report.
