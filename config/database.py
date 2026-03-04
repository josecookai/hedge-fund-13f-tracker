"""Database connection management."""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "tracker.db"


def _resolve_db_path() -> Path:
    return Path(os.getenv("DB_PATH", str(_DEFAULT_DB_PATH)))


# Module-level convenience — re-evaluated via _resolve_db_path() at call time
DB_PATH = _DEFAULT_DB_PATH


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    db_path = db_path or _resolve_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def db_session(db_path: Path | None = None):
    """Context manager yielding a connection with auto-commit/rollback."""
    conn = get_connection(db_path or _resolve_db_path())
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
