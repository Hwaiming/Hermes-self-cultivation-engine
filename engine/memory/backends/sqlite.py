"""
Memory Backend · SQLite + FTS5

Lightweight backend using stdlib only (sqlite3, json, re).
Zero external dependencies. Works everywhere.
"""
import json
import re
from pathlib import Path
from typing import Optional

from .base import MemoryBackend


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


class SQLiteBackend(MemoryBackend):
    """SQLite + FTS5 backed memory store."""

    def __init__(self, db_path: str = ""):
        import sqlite3
        from datetime import datetime, timezone

        if not db_path:
            db_path = str(Path(__file__).resolve().parent.parent.parent / ".scale" / "memory.db")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(SCHEMA_SQL)
        self._conn.commit()
        self._now = lambda: datetime.now(timezone.utc).isoformat()

    def close(self):
        self._conn.close()

    # ── FTS5 sanitize ──────────────────────────────────────

    @staticmethod
    def _fts5_clean(query: str) -> str:
        cleaned = re.sub(r'[?*^+~()"\-]', ' ', query)
        cleaned = ' '.join(cleaned.split())
        return cleaned[:200]

    # ── retain ─────────────────────────────────────────────

    def retain(self, content: str, context: str = "",
               tags: list = None, memory_type: str = "event") -> bool:
        tags = tags or []
        now = self._now()

        if memory_type == "fact":
            parts = content.split("::", 1)
            key = parts[0].strip()
            value = parts[1].strip() if len(parts) > 1 else ""
            tags_json = json.dumps(tags, ensure_ascii=False)
            self._conn.execute("""
                INSERT INTO facts(key, value, source, tags, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value=excluded.value, source=excluded.source,
                    tags=excluded.tags, updated_at=excluded.updated_at
            """, (key, value, context, tags_json, now, now))
            self._conn.commit()
            return True

        # Event
        all_tags = list(tags)
        if context and context not in all_tags:
            all_tags.append(context)
        tags_json = json.dumps(all_tags, ensure_ascii=False)
        self._conn.execute("""
            INSERT INTO events(event_type, summary, detail, tags, session_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (context or "generic", content[:500], content, tags_json, "", now))
        self._conn.commit()
        return True

    # ── recall ─────────────────────────────────────────────

    def recall(self, query: str, limit: int = 10) -> dict:
        result = {"facts": [], "events": [], "narratives": [], "sessions": []}

        # Facts: key/tag match
        rows = self._conn.execute(
            "SELECT * FROM facts WHERE key LIKE ? OR tags LIKE ? ORDER BY updated_at DESC LIMIT ?",
            (f"%{query}%", f"%{query}%", limit)
        ).fetchall()
        result["facts"] = [dict(r) for r in rows]

        # Events: FTS5 search
        safe_q = self._fts5_clean(query).replace("'", "''")
        if safe_q.strip():
            rows = self._conn.execute(
                f"SELECT e.* FROM events e JOIN events_fts fts ON e.id = fts.rowid "
                f"WHERE events_fts MATCH '{safe_q}' ORDER BY e.created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
            result["events"] = [dict(r) for r in rows]

        # Sessions: FTS5 search
        if safe_q.strip():
            rows = self._conn.execute(
                f"SELECT s.* FROM sessions s JOIN sessions_fts fts ON s.rowid = fts.rowid "
                f"WHERE sessions_fts MATCH '{safe_q}' ORDER BY s.started_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
            result["sessions"] = [dict(r) for r in rows]

        return result

    # ── reflect ────────────────────────────────────────────

    def reflect(self, question: str) -> dict:
        import re as re_mod
        terms = re_mod.findall(r'\b[a-zA-Z_]{3,}\b', question)
        cn_terms = re_mod.findall(r'[\u4e00-\u9fff]+', question)
        all_terms = terms + cn_terms

        all_events = []
        seen_ids = set()

        for term in all_terms[:5]:
            r = self.recall(term, limit=10)
            for e in r.get("events", []):
                if e["id"] not in seen_ids:
                    seen_ids.add(e["id"])
                    all_events.append(e)

        corrections = [e for e in all_events
                       if e.get("event_type") in ("correction", "detector")]

        return {
            "question": question,
            "correction_patterns": corrections,
            "relevant_insights": [],
            "relevant_facts": self.recall(question, limit=3).get("facts", []),
            "memory_count": len(corrections),
        }

    # ── stats ──────────────────────────────────────────────

    def stats(self) -> dict:
        fact_c = self._conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
        event_c = self._conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        session_c = self._conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        return {
            "backend": "sqlite",
            "db_path": self.db_path,
            "facts": fact_c,
            "events": event_c,
            "sessions": session_c,
        }
