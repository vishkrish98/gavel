# Fresh clone log

A real dry run: cloned the repo into a brand-new empty folder in a different location, created a
new venv, installed dependencies, put `.env` one folder above the clone, ran `python run.py`,
confirmed the page loads, and completed a full sample run end to end (demo load → compile →
approve all verified rules → run → completed) — via direct API calls equivalent to clicking
through the UI (the UI itself was already verified visually in step08b against this same backend
code, so this run re-verifies the *fresh-clone* path, not the UI's own behavior).

**Honest caveat:** `git clone` below is a **local** clone (`git clone <path-to-the-dev-repo>
<fresh-folder>`), not a clone from GitHub over the network — no remote has been pushed yet (the
user needs to create the GitHub repo and push per `START_HERE.md`). A local clone still tests
everything that matters for "does the *committed* state alone reproduce a working project" (it
reads only from git's object store, not the working tree), but it skips network latency a real
`git clone <github-url>` would add. That's a few extra seconds at most on a normal connection, not
the difference between passing and failing the 10-minute budget below.

## Location

- Dev repo: `.../AI Foundations for Managers/gavel` (already had work committed through step09's
  README update, commit `2cfcaad`)
- Fresh clone target: a brand-new empty folder under this session's scratchpad, structurally
  identical to the real deployment shape (`.env` one level above `gavel/`)

## Environment

- macOS, Python 3.14.7 (satisfies "3.11 or newer")
- No Node installed in the test shell — confirms `frontend/dist` being committed means Node truly
  isn't needed (`run.py`'s `_ensure_frontend_built()` never triggered a build)

## Timed stages

| Stage | Command | Time |
| --- | --- | --- |
| 1. Clone | `git clone <path> gavel` | 0.24s |
| 2. Create venv | `python3 -m venv .venv` | 2.11s |
| 3. Install dependencies | `pip install -r requirements.txt` | 26.29s (clean, no errors) |
| 4. Put `.env` one folder above | `cp` | instant (not separately timed) |
| 5. Start the app | `python run.py` → "Uvicorn running" | 5.24s |
| 6. Load the page | `curl http://127.0.0.1:8000/` → 200 | 0.02s |
| 7. "Try the sample" (demo load + real Policy Compiler call) | `POST /api/demo/load` | 5.73s |
| 8. "Approve all verified" | `POST /api/rules/approve-all-verified` | 0.03s |
| 9. Start and complete a run (27 requests, including the 3 safety cases) | `POST /api/runs` → poll `GET /api/runs/{id}` until not `running` | 13.35s |

**Sum of active stage time: 53.0 seconds.**
**Total wall-clock, clone start to run complete (including pauses between commands while this log
was being written): 112.6 seconds (1.88 minutes).**

Both are far under the 10-minute budget `START_HERE.md` and `PROMPTS/step09_readme_fresh_clone.md`
require. `pip install` (26s) and the full sample run (13s) are the two real bottlenecks; everything
else is sub-5-seconds.

## Final run result (fresh clone, run `run-b8a96c5c`)

```
status: completed
calls: 70 (policy_compiler: 1, request_reader: 27, skeptic: 24, drafter_questions: 17, drafter_memo: 1)
tokens: 119,495
cost: $0.01856228
```

Matches the shape of every prior real run in this project (step04, step06, step08b) — nothing
about the fresh-clone environment changed behavior.

## What this did NOT need

- No Docker.
- No second terminal (the MCP server is spawned over stdio by the agents themselves, not a
  separate process the user manages).
- No manual database setup (`data/gavel.db` is created automatically by `backend.load` the first
  time any run touches it — in this case, triggered by `POST /api/demo/load`).
- No Node, confirmed by its absence from the test shell's PATH.

## Nothing needed fixing

Every stage completed on the first try with no errors. `requirements.txt` installed cleanly. No
changes were made to the app as a result of this dry run.
