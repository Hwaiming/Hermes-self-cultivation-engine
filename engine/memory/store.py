"""
Hermes Memory System · SQLite + FTS5 Storage Backend

Persistent storage for three memory types:
- Facts: structured knowledge (user preferences, environment, conventions)
- Events: timestamped occurrences (corrections, detector hits, decisions)
- Sessions: narrative summaries with full-text search

Uses SQLite + FTS5 (built-in, no external dependencies).
Designed to pair with Hindsight's retain/recall/reflect protocol.
"""
import sqlite3
import json
import re
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone


# ── Schema ─────────────────────────────────────────────────

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS facts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    key         TEXT NOT NULL UNIQUE,
    value       TEXT NOT NULL,
    source      TEXT DEFAULT '',
    tags        TEXT DEFAULT '[]',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type  TEXT NOT NULL,
    summary     TEXT NOT NULL,
    detail      TEXT DEFAULT '',
    tags        TEXT DEFAULT '[]',
    session_id  TEXT DEFAULT '',
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT PRIMARY KEY,
    title       TEXT DEFAULT '',
    summary     TEXT DEFAULT '',
    token_count INTEGER DEFAULT 0,
    started_at  TEXT NOT NULL,
    ended_at    TEXT,
    tags        TEXT DEFAULT '[]'
);

CREATE VIRTUAL TABLE IF NOT EXISTS events_fts USING fts5(
    summary, detail, tags,
    content='events', content_rowid='id'
);

CREATE VIRTUAL TABLE IF NOT EXISTS sessions_fts USING fts5(
    title, summary, tags,
    content='sessions', content_rowid='rowid'
);

CREATE TRIGGER IF NOT EXISTS events_ai AFTER INSERT ON events BEGIN
    INSERT INTO events_fts(rowid, summary, detail, tags)
    VALUES (new.id, new.summary, new.detail, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS events_ad AFTER DELETE ON events BEGIN
    INSERT INTO events_fts(events_fts, rowid, summary, detail, tags)
    VALUES ('delete', old.id, old.summary, old.detail, old.tags);
END;

CREATE TRIGGER IF NOT EXISTS events_au AFTER UPDATE ON events BEGIN
    INSERT INTO events_fts(events_fts, rowid, summary, detail, tags)
    VALUES ('delete', old.id, old.summary, old.detail, old.tags);
    INSERT INTO events_fts(rowid, summary, detail, tags)
    VALUES (new.id, new.summary, new.detail, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS sessions_ai AFTER INSERT ON sessions BEGIN
    INSERT INTO sessions_fts(rowid, title, summary, tags)
    VALUES (new.rowid, new.title, new.summary, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS sessions_ad AFTER DELETE ON sessions BEGIN
    INSERT INTO sessions_fts(sessions_fts, rowid, title, summary, tags)
    VALUES ('delete', old.rowid, old.title, old.summary, old.tags);
END;

CREATE TRIGGER IF NOT EXISTS sessions_au AFTER UPDATE ON sessions BEGIN
    INSERT INTO sessions_fts(sessions_fts, rowid, title, summary, tags)
    VALUES ('delete', old.rowid, old.title, old.summary, old.tags);
    INSERT INTO sessions_fts(rowid, title, summary, tags)
    VALUES (new.rowid, new.title, new.summary, new.tags);
END;
"""


# ── Store ──────────────────────────────────────────────────

class MemoryStore:
    """SQLite-backed persistent memory store with FTS5 search."""

    def __init__(self, db_path: str = ""):
        if not db_path:
            db_path = str(Path(__file__).resolve().parent.parent / ".scale" / "memory.db")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(SCHEMA_SQL)
        self._conn.commit()

    def close(self):
        self._conn.close()

    # ── FTS5 Query Sanitization ────────────────────────────

    @staticmethod
    def _fts5_clean(query: str) -> str:
        """Strip FTS5 operator chars, keep plain text search terms.
        FTS5 treats ? * ^ + - ~ ( ) as operators — strip them."""
        cleaned = re.sub(r'[?*^+~()"\-]', ' ', query)
        cleaned = ' '.join(cleaned.split())
        return cleaned[:200]

    # ── Facts ──────────────────────────────────────────────

    def set_fact(self, key: str, value: str, source: str = "", tags: list = None) -> bool:
        """Store or update a structured fact."""
        now = datetime.now(timezone.utc).isoformat()
        tags_json = json.dumps(tags or [], ensure_ascii=False)
        self._conn.execute("""
            INSERT INTO facts(key, value, source, tags, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value=excluded.value,
                source=excluded.source,
                tags=excluded.tags,
                updated_at=excluded.updated_at
        """, (key, value, source, tags_json, now, now))
        self._conn.commit()
        return True

    def get_fact(self, key: str) -> Optional[dict]:
        """Retrieve a fact by key."""
        row = self._conn.execute(
            "SELECT * FROM facts WHERE key = ?", (key,)
        ).fetchone()
        return dict(row) if row else None

    def search_facts(self, query: str, limit: int = 10) -> list:
        """Search facts by key prefix or tag match."""
        rows = self._conn.execute("""
            SELECT * FROM facts
            WHERE key LIKE ? OR tags LIKE ?
            ORDER BY updated_at DESC
            LIMIT ?
        """, (f"%{query}%", f"%{query}%", limit)).fetchall()
        return [dict(r) for r in rows]

    def delete_fact(self, key: str) -> bool:
        self._conn.execute("DELETE FROM facts WHERE key = ?", (key,))
        self._conn.commit()
        return True

    # ── Events ─────────────────────────────────────────────

    def add_event(self, event_type: str, summary: str, detail: str = "",
                  tags: list = None, session_id: str = "") -> int:
        """Record an event (correction, detector hit, decision)."""
        now = datetime.now(timezone.utc).isoformat()
        tags_json = json.dumps(tags or [], ensure_ascii=False)
        cursor = self._conn.execute("""
            INSERT INTO events(event_type, summary, detail, tags, session_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (event_type, summary, detail, tags_json, session_id, now))
        self._conn.commit()
        return cursor.lastrowid

    def search_events(self, query: str, limit: int = 20, event_type: str = "") -> list:
        """Full-text search across events."""
        safe_q = self._fts5_clean(query).replace("'", "''")
        if not safe_q.strip():
            return self.recent_events(limit=limit, event_type=event_type)
        if event_type:
            rows = self._conn.execute(f"""
                SELECT e.* FROM events e
                JOIN events_fts fts ON e.id = fts.rowid
                WHERE events_fts MATCH '{safe_q}' AND e.event_type = ?
                ORDER BY e.created_at DESC
                LIMIT ?
            """, (event_type, limit)).fetchall()
        else:
            rows = self._conn.execute(f"""
                SELECT e.* FROM events e
                JOIN events_fts fts ON e.id = fts.rowid
                WHERE events_fts MATCH '{safe_q}'
                ORDER BY e.created_at DESC
                LIMIT ?
            """, (limit,)).fetchall()
        return [dict(r) for r in rows]

    def recent_events(self, limit: int = 20, event_type: str = "") -> list:
        """Most recent events (no search)."""
        if event_type:
            rows = self._conn.execute(
                "SELECT * FROM events WHERE event_type = ? ORDER BY created_at DESC LIMIT ?",
                (event_type, limit)
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM events ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    # ── Sessions ───────────────────────────────────────────

    def start_session(self, session_id: str, title: str = "", tags: list = None) -> bool:
        """Begin a new session."""
        now = datetime.now(timezone.utc).isoformat()
        tags_json = json.dumps(tags or [], ensure_ascii=False)
        self._conn.execute("""
            INSERT OR IGNORE INTO sessions(id, title, started_at, tags)
            VALUES (?, ?, ?, ?)
        """, (session_id, title, now, tags_json))
        self._conn.commit()
        return True

    def end_session(self, session_id: str, summary: str = "", token_count: int = 0) -> bool:
        """End a session with summary."""
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute("""
            UPDATE sessions SET summary = ?, token_count = ?, ended_at = ?
            WHERE id = ?
        """, (summary, token_count, now, session_id))
        self._conn.commit()
        return True

    def search_sessions(self, query: str, limit: int = 10) -> list:
        """Full-text search across sessions."""
        safe_q = self._fts5_clean(query).replace("'", "''")
        if not safe_q.strip():
            return self.recent_sessions(limit=limit)
        rows = self._conn.execute(f"""
            SELECT s.* FROM sessions s
            JOIN sessions_fts fts ON s.rowid = fts.rowid
            WHERE sessions_fts MATCH '{safe_q}'
            ORDER BY s.started_at DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]

    def recent_sessions(self, limit: int = 10) -> list:
        rows = self._conn.execute(
            "SELECT * FROM sessions ORDER BY started_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Stats ──────────────────────────────────────────────

    def stats(self) -> dict:
        """Memory store statistics."""
        fact_count = self._conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
        event_count = self._conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        session_count = self._conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        return {
            "facts": fact_count,
            "events": event_count,
            "sessions": session_count,
            "db_path": self.db_path,
        }
