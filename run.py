"""One-command start for Gavel: python run.py

Loads .env (repo folder first, then one level above), picks a free port starting at 8000,
starts the FastAPI backend (which serves the built frontend), and prints the URL. No Docker, no
second terminal, no manual database setup.

The built frontend (frontend/dist) is committed to the repo, so a fresh clone needs no Node to
run the app at all. If frontend/dist is ever missing (e.g. someone deleted it, or a .gitignore
mistake), this will build it automatically -- but only if Node is present; otherwise it prints a
clear message and still starts the backend (API-only, no UI) rather than failing outright.

The MCP server is not a separate long-running process here: once mcp_server/server.py exists
(step02), agents spawn it over stdio themselves, the same way backend/agents.py does in the
reference chassis -- nothing to launch from run.py for that.
"""

from __future__ import annotations

import shutil
import socket
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from env_loader import require_env

FRONTEND_DIR = ROOT / "frontend"
FRONTEND_DIST = FRONTEND_DIR / "dist"


def _ensure_frontend_built() -> None:
    if FRONTEND_DIST.exists():
        return
    node = shutil.which("node")
    npm = shutil.which("npm")
    if not node or not npm:
        print(
            "frontend/dist is missing and Node/npm were not found, so it can't be built -- "
            "starting the backend only (no UI). Install Node 20+ and run "
            "`npm install && npm run build` inside frontend/, then restart."
        )
        return
    print("frontend/dist is missing but Node is available -- building the frontend once...")
    subprocess.run(["npm", "install"], cwd=FRONTEND_DIR, check=True)
    subprocess.run(["npm", "run", "build"], cwd=FRONTEND_DIR, check=True)


def _first_free_port(start: int = 8000, attempts: int = 20) -> int:
    for port in range(start, start + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError(f"No free port found in range {start}-{start + attempts - 1}")


def main() -> None:
    require_env(["PORTKEY_API_KEY"])
    _ensure_frontend_built()

    import uvicorn

    port = _first_free_port(8000)
    print(f"Gavel starting at http://127.0.0.1:{port}")
    uvicorn.run("backend.main:app", host="127.0.0.1", port=port, reload=False)


if __name__ == "__main__":
    main()
