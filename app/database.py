"""SQLite database layer for the grievance system.

Plain sqlite3 (stdlib) keeps the hackathon deploy simple. Tables:
  departments, keywords, complaints, status_history, notifications, llm_feedback
"""
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone

from .config import settings

_lock = threading.RLock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS departments (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    code          TEXT UNIQUE NOT NULL,
    name          TEXT NOT NULL,
    description   TEXT DEFAULT '',
    contact_email TEXT DEFAULT '',
    contact_phone TEXT DEFAULT '',
    color         TEXT DEFAULT '#4f46e5'
);

CREATE TABLE IF NOT EXISTS keywords (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    department_id INTEGER NOT NULL REFERENCES departments(id),
    keyword       TEXT NOT NULL,
    weight        REAL NOT NULL DEFAULT 1.0,
    is_negative   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS complaints (
    id                    TEXT PRIMARY KEY,
    tracking_id           TEXT UNIQUE NOT NULL,
    title                 TEXT NOT NULL,
    description           TEXT NOT NULL,
    category              TEXT DEFAULT '',
    location              TEXT DEFAULT '',
    city                  TEXT DEFAULT '',
    pincode               TEXT DEFAULT '',
    contact_name          TEXT DEFAULT '',
    contact_email         TEXT DEFAULT '',
    contact_phone         TEXT DEFAULT '',
    user_id               INTEGER REFERENCES users(id),
    department_id         INTEGER REFERENCES departments(id),
    department_confidence REAL DEFAULT 0.0,
    routing_method        TEXT DEFAULT 'classifier',
    matched_keywords      TEXT DEFAULT '',
    status                TEXT NOT NULL DEFAULT 'PENDING',
    priority              TEXT NOT NULL DEFAULT 'MEDIUM',
    admin_notes           TEXT DEFAULT '',
    created_at            TEXT NOT NULL,
    updated_at            TEXT NOT NULL,
    resolved_at           TEXT
);

CREATE TABLE IF NOT EXISTS status_history (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id TEXT NOT NULL REFERENCES complaints(id),
    status       TEXT NOT NULL,
    note         TEXT DEFAULT '',
    changed_by   TEXT DEFAULT 'system',
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notifications (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id TEXT NOT NULL,
    channel      TEXT NOT NULL,          -- SMS | EMAIL
    recipient    TEXT NOT NULL,
    subject      TEXT DEFAULT '',
    message      TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'SENT',
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS llm_feedback (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id           TEXT NOT NULL,
    llm_department_id      INTEGER,
    llm_confidence         REAL DEFAULT 0.0,
    classifier_department_id INTEGER,
    agreed                 INTEGER DEFAULT 0,
    created_at             TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name     TEXT NOT NULL,
    email         TEXT UNIQUE,
    phone         TEXT UNIQUE,
    city          TEXT DEFAULT '',
    password_hash TEXT DEFAULT '',
    role          TEXT NOT NULL DEFAULT 'citizen',   -- citizen | admin | department
    department_id INTEGER REFERENCES departments(id),
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS feedback (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id TEXT NOT NULL REFERENCES complaints(id),
    user_id      INTEGER,
    rating       INTEGER NOT NULL DEFAULT 5,          -- 1..5 stars
    comment      TEXT DEFAULT '',
    channel      TEXT DEFAULT 'web',
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS department_complaints (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    department_id INTEGER NOT NULL REFERENCES departments(id),
    complaint_id  TEXT NOT NULL REFERENCES complaints(id),
    assigned_at   TEXT NOT NULL,
    sla_due_at    TEXT NOT NULL,
    queue_position INTEGER DEFAULT 1,
    UNIQUE(department_id, complaint_id)
);

CREATE INDEX IF NOT EXISTS idx_complaints_dept ON complaints(department_id);
CREATE INDEX IF NOT EXISTS idx_complaints_status ON complaints(status);
CREATE INDEX IF NOT EXISTS idx_complaints_created ON complaints(created_at);
CREATE INDEX IF NOT EXISTS idx_history_complaint ON status_history(complaint_id);
CREATE INDEX IF NOT EXISTS idx_feedback_complaint ON feedback(complaint_id);
CREATE INDEX IF NOT EXISTS idx_deptq_dept ON department_complaints(department_id);
"""


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


@contextmanager
def db():
    with _lock:
        conn = get_conn()
        try:
            conn.execute("BEGIN")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def init_db() -> None:
    with _lock:
        conn = get_conn()
        try:
            conn.executescript(SCHEMA)
            conn.commit()
            _migrate(conn)
            conn.commit()
        finally:
            conn.close()


def _migrate(conn: sqlite3.Connection) -> None:
    """Add columns that newer versions introduced, without dropping data."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(complaints)").fetchall()}
    if "user_id" not in cols:
        conn.execute("ALTER TABLE complaints ADD COLUMN user_id INTEGER REFERENCES users(id)")


def execute(sql: str, params: tuple = ()) -> None:
    with db() as conn:
        conn.execute(sql, params)


def fetch_all(sql: str, params: tuple = ()) -> list[dict]:
    with db() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def fetch_one(sql: str, params: tuple = ()) -> dict | None:
    with db() as conn:
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None
