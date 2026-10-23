"""Shared .env loader used by both backend/main.py and mcp_server/server.py.

Looks for .env in the repo folder first, then one level above it (CONTEXT.md hard rule 2).
Never overwrites a variable already set in the real environment. Does not print or log values.
"""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent


def _load_dotenv_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if key and key not in os.environ:
            os.environ[key] = value


def load_env() -> list[Path]:
    """Load .env from the repo folder, then the parent folder. Returns the paths that existed."""
    candidates = [REPO_ROOT / ".env", REPO_ROOT.parent / ".env"]
    loaded = []
    for path in candidates:
        if path.exists():
            _load_dotenv_file(path)
            loaded.append(path)
    return loaded


def require_env(keys: list[str]) -> None:
    """Load .env (repo folder, then parent) and fail with a friendly message if any key is
    still missing, naming both locations that were checked."""
    load_env()
    missing = [key for key in keys if not os.environ.get(key)]
    if missing:
        repo_env = REPO_ROOT / ".env"
        parent_env = REPO_ROOT.parent / ".env"
        raise RuntimeError(
            f"Missing required environment variable(s): {', '.join(missing)}.\n"
            f"Gavel looks for a .env file in two places:\n"
            f"  1. {repo_env}\n"
            f"  2. {parent_env}\n"
            f"Create a .env in one of those with lines like:\n"
            f"  PORTKEY_API_KEY=your-course-key\n"
            f"See .env.example for the full list of names."
        )
