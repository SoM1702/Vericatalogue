from __future__ import annotations

import os
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
DATA_DIR = BACKEND_ROOT / "data"
DEMO_DIR = BACKEND_ROOT / "demo_data"


def _load_local_env(path: Path) -> None:
    """Load a small local .env file without adding a runtime dependency or overriding shell values."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip().strip('"').strip("'")


_load_local_env(BACKEND_ROOT / ".env")

DATABASE_URL = os.getenv("VERICATALOG_DATABASE_URL", "")
DB_PATH = Path(os.getenv("VERICATALOG_DB_PATH", DATA_DIR / "vericatalog.sqlite3"))
UPLOAD_DIR = Path(os.getenv("VERICATALOG_UPLOAD_DIR", DATA_DIR / "uploads"))
MAX_UPLOAD_BYTES = int(os.getenv("VERICATALOG_MAX_UPLOAD_BYTES", "5242880"))
CORS_ORIGINS = os.getenv(
    "VERICATALOG_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",")
AI_ENABLED = os.getenv("VERICATALOG_AI_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
AI_API_KEY = os.getenv("VERICATALOG_AI_API_KEY", "")
AI_BASE_URL = os.getenv("VERICATALOG_AI_BASE_URL", "")
AI_MODEL = os.getenv("VERICATALOG_AI_MODEL", "")
AI_TIMEOUT_SECONDS = float(os.getenv("VERICATALOG_AI_TIMEOUT_SECONDS", "15"))
AI_BATCH_LIMIT = int(os.getenv("VERICATALOG_AI_BATCH_LIMIT", "10"))


def ai_is_configured() -> bool:
    return AI_ENABLED and bool(AI_API_KEY and AI_BASE_URL and AI_MODEL)


def ensure_runtime_directories() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
