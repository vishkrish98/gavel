"""One-command start for Gavel: python run.py

Loads .env (repo folder first, then one level above), picks a free port starting at 8000,
starts the FastAPI backend (which serves the built frontend once it exists), and prints the
URL. No Docker, no second terminal, no manual database setup.

The MCP server is not a separate long-running process here: once mcp_server/server.py exists
(step02), agents spawn it over stdio themselves, the same way backend/agents.py does in the
reference chassis -- nothing to launch from run.py for that.
"""

from __future__ import annotations

import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from env_loader import require_env


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

    import uvicorn

    port = _first_free_port(8000)
    print(f"Gavel starting at http://127.0.0.1:{port}")
    uvicorn.run("backend.main:app", host="127.0.0.1", port=port, reload=False)


if __name__ == "__main__":
    main()
