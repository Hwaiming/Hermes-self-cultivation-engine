"""
Hermes Memory System · Core Engine

Unified interface wrapping any MemoryBackend.
Auto-detects Hindsight if available, falls back to SQLite.

Usage:
    from engine.memory.core import MemoryEngine

    # Auto-detect
    mem = MemoryEngine()
    mem.retain("user preference", "prefers concise responses")

    # Force specific backend
    mem = MemoryEngine(backend="sqlite")
    mem = MemoryEngine(backend="hindsight")
"""
import json
import re
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone

from .backends.base import MemoryBackend
from .backends.sqlite import SQLiteBackend
from .backends.hindsight import HindsightBackend
from .narrative import NarrativeLog


_DEFAULT_DIR = Path(__file__).resolve().parent.parent / ".scale"

# Backend registry
BACKENDS = {
    "sqlite": SQLiteBackend,
    "hindsight": HindsightBackend,
}


def _detect_backend(backend_name: str = "") -> MemoryBackend:
    """Select backend: explicit name, auto-detect, or fallback to sqlite."""
    if backend_name:
        cls = BACKENDS.get(backend_name)
        if cls:
            return cls()
        raise ValueError(f"Unknown backend: {backend_name}. Available: {list(BACKENDS.keys())}")

    # Auto-detect: try Hindsight, verify with a test retain
    try:
        hb = HindsightBackend()
        if hb.available:
            # Verify it actually works
            test_ok = hb.retain("__probe__", "__init__", ["probe"])
            if test_ok:
                return hb
    except Exception:
        pass

    # Fallback to SQLite
    return SQLiteBackend()


class MemoryEngine:
    """Unified memory interface — auto-selects backend.

    Three memory tiers:
    - Events (default): timestamped, searchable
    - Facts: structured key-value
    - Narrative: story-first, append-only

    Protocol:
        retain(content, context, tags, memory_type)
        recall(query)
        reflect(question)
    """

    def __init__(self, backend: str = "", db_path: str = "",
                 narrative_path: str = ""):
        self._backend = _detect_backend(backend)

        # Narrative log (backend-independent, append-only JSONL)
        if not narrative_path:
            narrative_path = str(_DEFAULT_DIR / "narrative.jsonl")
        self.narrative = NarrativeLog(narrative_path)

        self._session_id = ""

    @property
    def backend(self) -> MemoryBackend:
        return self._backend

    @property
    def backend_name(self) -> str:
        return self._backend.name

    # ── Session lifecycle ──────────────────────────────────

    def begin_session(self, session_id: str = "", title: str = ""):
        if not session_id:
            session_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self._session_id = session_id
        return session_id

    def end_session(self, summary: str = "", token_count: int = 0):
        self._session_id = ""

    @property
    def session_id(self) -> str:
        return self._session_id

    # ── retain ─────────────────────────────────────────────

    def retain(self, content: str, context: str = "",
               tags: list = None, memory_type: str = "event") -> bool:
        """Store into memory.

        Types:
        - "event" (default): searchable via backend
        - "fact": structured key-value (content="key::value")
        - "narrative": story-first, always to JSONL log
        """
        tags = tags or []

        # Narrative always goes to JSONL log (backend-independent)
        if memory_type == "narrative":
            self.narrative.append(
                session_id=self._session_id,
                entry_type="narrative",
                scene=content,
                transformation=context,
                tags=tags,
            )
            return True

        # Facts and events go to backend
        if memory_type == "fact":
            return self._backend.retain(content, context, tags, "fact")

        # Event: include context as searchable tag
        all_tags = list(tags)
        if context and context not in all_tags:
            all_tags.append(context)
        return self._backend.retain(content, context, all_tags, "event")

    # ── recall ─────────────────────────────────────────────

    def recall(self, query: str, limit: int = 10) -> dict:
        """Search across backend + narrative log."""
        result = self._backend.recall(query, limit)

        # Supplement with narrative search
        result["narratives"] = self.narrative.search(query, limit=limit)

        return result

    # ── reflect ────────────────────────────────────────────

    def reflect(self, question: str) -> dict:
        """Synthesize across memories."""
        return self._backend.reflect(question)

    # ── Integration with Self-Cultivation Engine ───────────

    def capture_detector_result(self, detector_name: str, passed: bool,
                                 message: str, detail: str = ""):
        """Auto-retain when a detector fires."""
        if passed:
            return
        self.retain(
            f"[{detector_name}] {message}",
            context="detector",
            tags=["detector", detector_name],
        )

    def capture_correction(self, scene: str, transformation: str = ""):
        """Auto-retain a user correction as narrative."""
        self.narrative.append(
            session_id=self._session_id,
            entry_type="correction",
            scene=scene,
            transformation=transformation or "Not yet internalized",
            tags=["correction"],
        )

    # ── Stats ──────────────────────────────────────────────

    def stats(self) -> dict:
        s = self._backend.stats()
        s["narrative_entries"] = self.narrative.count()
        s["session_active"] = bool(self._session_id)
        return s

    def close(self):
        self._backend.close()
