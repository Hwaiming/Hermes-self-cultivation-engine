"""
Hermes Memory System · Core Engine

Unified interface wrapping MemoryStore (SQLite + FTS5) and NarrativeLog (JSONL).
Mirrors Hindsight's retain/recall/reflect protocol for compatibility.

Usage:
    from engine.memory.core import MemoryEngine

    mem = MemoryEngine()
    mem.retain("user_preference", "Prefers concise responses", tags=["preference"])
    results = mem.recall("user preference")
    reflection = mem.reflect("What patterns repeat across sessions?")
"""
import json
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone

from .store import MemoryStore
from .narrative import NarrativeLog


# Default paths (under .scale/)
_DEFAULT_DIR = Path(__file__).resolve().parent.parent / ".scale"


class MemoryEngine:
    """Unified memory interface.

    Three memory tiers:
    1. Facts (structured, key-value, over-writable) — user prefs, env facts
    2. Events (timestamped, searchable) — corrections, detector hits, decisions
    3. Narrative (append-only, story-first) — scenes with transformations

    Protocol (Hindsight-compatible):
    - retain(content, context, tags) → store something
    - recall(query) → search for relevant memories
    - reflect(question) → synthesize across memories
    """

    def __init__(self, db_path: str = "", narrative_path: str = ""):
        if not db_path:
            db_path = str(_DEFAULT_DIR / "memory.db")
        if not narrative_path:
            narrative_path = str(_DEFAULT_DIR / "narrative.jsonl")
        self.store = MemoryStore(db_path)
        self.narrative = NarrativeLog(narrative_path)
        self._session_id = ""

    # ── Session lifecycle ──────────────────────────────────

    def begin_session(self, session_id: str = "", title: str = ""):
        """Start tracking a new session."""
        if not session_id:
            session_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self._session_id = session_id
        self.store.start_session(session_id, title=title)
        return session_id

    def end_session(self, summary: str = "", token_count: int = 0):
        """End current session with summary."""
        if self._session_id:
            self.store.end_session(self._session_id, summary, token_count)
            self._session_id = ""

    @property
    def session_id(self) -> str:
        return self._session_id

    # ── retain ─────────────────────────────────────────────

    def retain(self, content: str, context: str = "",
               tags: list = None, memory_type: str = "event") -> bool:
        """Store something into memory.

        memory_type:
        - "event" (default): timestamped occurrence, searchable via FTS5
        - "fact": structured key-value (content is "key::value")
        - "narrative": story-first scene with transformation
        """
        tags = tags or []

        if memory_type == "fact":
            # content format: "key::value"
            parts = content.split("::", 1)
            key = parts[0].strip()
            value = parts[1].strip() if len(parts) > 1 else ""
            self.store.set_fact(key, value, source=context, tags=tags)
            return True

        if memory_type == "narrative":
            # content = scene, context = transformation
            self.narrative.append(
                session_id=self._session_id,
                entry_type="narrative",
                scene=content,
                transformation=context,
                tags=tags,
            )
            return True

        # Default: event — include context as a searchable tag
        all_tags = list(tags or [])
        if context and context not in all_tags:
            all_tags.append(context)
        self.store.add_event(
            event_type=context or "generic",
            summary=content[:500],
            detail=content,
            tags=all_tags,
            session_id=self._session_id,
        )
        return True

    # ── recall ─────────────────────────────────────────────

    def recall(self, query: str, limit: int = 10) -> dict:
        """Search across all memory tiers.

        Returns structured results grouped by type.
        """
        result = {
            "query": query,
            "facts": [],
            "events": [],
            "narratives": [],
            "sessions": [],
        }

        # Search facts (key/value match)
        result["facts"] = self.store.search_facts(query, limit=limit)

        # Search events (FTS5)
        result["events"] = self.store.search_events(query, limit=limit)

        # Search narrative log
        result["narratives"] = self.narrative.search(query, limit=limit)

        # Search sessions
        result["sessions"] = self.store.search_sessions(query, limit=limit)

        return result

    # ── reflect ────────────────────────────────────────────

    def reflect(self, question: str) -> dict:
        """Synthesize across memories to answer a question.

        Gathers relevant context from all tiers and returns
        a structured reflection with evidence sources.
        """
        # Extract key terms: nouns, tags, meaningful words
        import re, json
        terms = re.findall(r'\b[a-zA-Z_]{3,}\b', question)
        # Also extract Chinese characters
        chinese_terms = re.findall(r'[\u4e00-\u9fff]+', question)
        all_terms = terms + chinese_terms

        # Try each term individually, combine results
        all_events = []
        all_narratives = []
        all_facts = []

        for term in all_terms[:5]:  # Limit to 5 terms
            memories = self.recall(term, limit=10)
            all_events.extend(memories.get("events", []))
            all_narratives.extend(memories.get("narratives", []))
            all_facts.extend(memories.get("facts", []))

        # Deduplicate by id
        seen_ids = set()
        deduped_events = []
        for e in all_events:
            if e["id"] not in seen_ids:
                seen_ids.add(e["id"])
                deduped_events.append(e)

        # Extract correction patterns
        corrections = [e for e in deduped_events
                       if e.get("event_type") in ("correction", "detector")]

        # Extract insights from narrative (deduplicate by checking if already in all_narratives)
        seen_narr = set()
        deduped_narr = []
        for n in all_narratives:
            key = json.dumps(n, sort_keys=True)
            if key not in seen_narr:
                seen_narr.add(key)
                deduped_narr.append(n)

        # Extract relevant facts (deduplicate by key)
        seen_fact = set()
        deduped_facts = []
        for f in all_facts:
            if f["key"] not in seen_fact:
                seen_fact.add(f["key"])
                deduped_facts.append(f)

        return {
            "question": question,
            "correction_patterns": corrections,
            "relevant_insights": deduped_narr,
            "relevant_facts": deduped_facts,
            "memory_count": len(corrections) + len(deduped_narr) + len(deduped_facts),
        }

    # ── Integration with Self-Cultivation Engine ───────────

    def capture_detector_result(self, detector_name: str, passed: bool,
                                 message: str, detail: str = ""):
        """Auto-retain when a detector fires (called by check.py)."""
        if passed:
            return  # Only capture failures for now

        self.store.add_event(
            event_type="detector",
            summary=f"[{detector_name}] {message}",
            detail=detail,
            tags=["detector", detector_name],
            session_id=self._session_id,
        )

    def capture_correction(self, scene: str, transformation: str = ""):
        """Auto-retain a user correction."""
        self.narrative.append(
            session_id=self._session_id,
            entry_type="correction",
            scene=scene,
            transformation=transformation or "Not yet internalized",
            tags=["correction"],
        )

    # ── Stats ──────────────────────────────────────────────

    def stats(self) -> dict:
        """Memory statistics."""
        s = self.store.stats()
        n = self.narrative.stats()
        s["narrative_entries"] = n["entries"]
        s["session_active"] = bool(self._session_id)
        return s

    def close(self):
        self.store.close()
