# AI prompts log

Every prompt used to build this project is saved as a file in PROMPTS/. After each step, add a line here.

| Step | Prompt file | What the coder did / what I changed |
| --- | --- | --- |
| step00 | PROMPTS/step00_skeleton.md | Cloned vishkrish98/hw5 as reference chassis (outside repo, not committed). Created backend/, mcp_server/, frontend/, output/, tests/; requirements.txt pinned to the versions hw5 uses (fastapi 0.142.2, uvicorn 0.54.0, fastmcp 4.0.11, pydantic 2.13.5, pydantic-ai 2.54.0); root-level env_loader.py (checks repo folder .env, then parent folder .env, friendly error naming both if PORTKEY_API_KEY missing); run.py (picks free port from 8000, starts backend, prints URL); backend/main.py placeholder page + /health route, mounts frontend/dist once it exists. Proved run.py works with .env in parent only, then in repo only, then moved it back to parent. venv created, deps installed clean. |
| step01 | PROMPTS/step01_data_layer.md | |
| step02 | PROMPTS/step02_mcp_tools.md | |
| step03 | PROMPTS/step03_engine.md | |
| step04 | PROMPTS/step04_agents.md | |
| step05 | PROMPTS/step05_token_logging.md | |
| step06 | PROMPTS/step06_benchmark.md | |
| step07 | PROMPTS/step07_safety.md | |
| step08a | PROMPTS/step08a_backend_routes.md | |
| step08b | PROMPTS/step08b_frontend.md | |
| step08c | PROMPTS/step08c_portability.md | |
| step09 | PROMPTS/step09_readme_fresh_clone.md | |
| step10 | PROMPTS/step10_evidence_pack.md | |
| step11a | PROMPTS/step11a_report.md | |
| step11b | PROMPTS/step11b_slides.md | |
