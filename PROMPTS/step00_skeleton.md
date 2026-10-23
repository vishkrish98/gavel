Read CONTEXT.md first. Do Step 0 only.

- Clone https://github.com/vishkrish98/hw5 into a temporary folder outside this repo (never commit it). Use it as the reference chassis.
- Create folders backend/, mcp_server/, frontend/, output/, tests/ (data/, evidence/, tools/ and PROMPTS/ already exist; do not touch data/), plus README.md, requirements.txt (pinned versions), run.py, harness.md. .gitignore, .env.example, CONTEXT.md and AI_prompts.md already exist; keep them.
- Write one shared env-loader helper used by the backend and the MCP server. It checks the repo folder, then one level above, and fails with a friendly message naming both locations if PORTKEY_API_KEY is missing.
- run.py starts the backend and serves a placeholder page.
- Prove it: run python run.py with .env in the parent folder and show it starting. Then move .env into the repo folder, run again, and show that works too. Move it back to the parent folder afterwards.
- git init and make the first commit. Do not push.
Stop and report.
