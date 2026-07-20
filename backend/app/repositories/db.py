import sqlite3
from pathlib import Path

from app.config import get_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS commitments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_title TEXT NOT NULL,
    actor_type TEXT,
    actor_name TEXT,
    beneficiary TEXT,
    due_at TEXT,
    due_text TEXT,
    confidence REAL,
    source_evidence TEXT,
    source_channel TEXT,
    status TEXT NOT NULL DEFAULT 'staged',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def get_connection() -> sqlite3.Connection:
    settings = get_settings()
    db_path = Path(settings.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)
    return conn
