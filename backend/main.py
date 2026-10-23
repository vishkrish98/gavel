"""FastAPI backend for Gavel.

Run with `python run.py` from the repo root (never `uvicorn backend.main:app` directly in
normal use, since run.py is what loads .env and picks a free port). Step00: this just proves
the env-loader and serves a placeholder page. Real routes (policy, requests, engine, agents,
scenarios) are added in step08a; the built frontend is mounted here once step08b exists.
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
ROOT = BACKEND_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from env_loader import require_env

require_env(["PORTKEY_API_KEY"])

app = FastAPI(title="Gavel")

FRONTEND_DIST = ROOT / "frontend" / "dist"

PLACEHOLDER_HTML = """<!doctype html>
<html>
<head><title>Gavel</title></head>
<body style="font-family: sans-serif; max-width: 640px; margin: 4rem auto;">
<h1>Gavel is running</h1>
<p>Backend is up. The frontend is not built yet (that lands in step08b).</p>
<p>Health check: <a href="/health">/health</a></p>
</body>
</html>"""


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
else:

    @app.get("/", response_class=HTMLResponse)
    def placeholder() -> str:
        return PLACEHOLDER_HTML
