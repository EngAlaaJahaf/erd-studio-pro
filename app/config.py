"""Application settings loaded from environment / .env (keeps the existing
behaviour: values can also be configured from the UI and stored in SQLite).

This module deliberately avoids a hard third-party settings library so it stays
compatible with the existing requirements.txt. Values are read from OS env,
falling back to a local .env file at the project root, then defaults.
"""
from __future__ import annotations

import os
from pathlib import Path

# --- Project paths (derived from this file, so the package location is stable) ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = PROJECT_ROOT / "static"
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "app.db"

# --- Load .env into environment if a file exists (simple, dependency-free) ---
_ENV_FILE = PROJECT_ROOT / ".env"
if _ENV_FILE.exists():
    try:
        for _line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
            _line = _line.strip()
            if not _line or _line.startswith("#") or "=" not in _line:
                continue
            _key, _val = _line.split("=", 1)
            _key = _key.strip()
            _val = _val.strip().strip("'\"")
            if _key and _key not in os.environ:
                os.environ[_key] = _val
    except Exception:  # never let a bad .env stop the server
        pass


def _get(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


# --- Server ---
SERVER_HOST: str = _get("SERVER_HOST", "0.0.0.0")
SERVER_PORT: int = int(_get("SERVER_PORT", "8500"))

# --- Oracle (defaults; can be overridden from the UI) ---
ORACLE_USER: str = _get("ORACLE_USER", "TESTR")
ORACLE_PASSWORD: str = _get("ORACLE_PASSWORD", "TESTR")
ORACLE_HOST: str = _get("ORACLE_HOST", "localhost")
ORACLE_PORT: int = int(_get("ORACLE_PORT", "1521"))
ORACLE_SERVICE: str = _get("ORACLE_SERVICE", "orclpdb")

# --- AI Assistant (defaults; can be overridden from the UI) ---
AI_PROVIDER: str = _get("AI_PROVIDER", "local")
AI_BASE_URL: str = _get("AI_BASE_URL", "http://localhost:11434/v1")
AI_API_KEY: str = _get("AI_API_KEY", "")
AI_MODEL: str = _get("AI_MODEL", "gpt-4o-mini")
AI_TEMPERATURE: float = float(_get("AI_TEMPERATURE", "0.4"))
