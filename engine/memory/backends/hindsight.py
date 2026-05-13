"""
Memory Backend · Hindsight

Wraps Hindsight's HTTP API (Docker, localhost:8888).
Used when Hindsight is available — provides semantic search,
entity extraction, and cross-session synthesis.

Auto-detected: if localhost:8888 responds, use Hindsight.
Fallback: SQLiteBackend.
"""
import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

from .base import MemoryBackend


# Default Hindsight endpoint (Docker container)
HINDSIGHT_BASE = "http://localhost:8888"
HINDSIGHT_BANK = "hermes-memory"
HINDSIGHT_TIMEOUT = 10  # seconds


class HindsightBackend(MemoryBackend):
    """Hindsight HTTP API backend.

    Maps retain/recall/reflect to Hindsight's REST endpoints.
    Falls back to best-effort on connection errors.
    """

    def __init__(self, base_url: str = HINDSIGHT_BASE,
                 bank: str = HINDSIGHT_BANK, timeout: int = HINDSIGHT_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.bank = bank
        self.timeout = timeout
        self._available = self._ping()

    def _ping(self) -> bool:
        """Check if Hindsight is reachable."""
        try:
            req = urllib.request.Request(f"{self.base_url}/health", method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                return resp.status == 200
        except (urllib.error.URLError, ConnectionRefusedError, OSError):
            return False

    def _api_post(self, path: str, data: dict) -> Optional[dict]:
        """Make a POST request to Hindsight API."""
        try:
            body = json.dumps(data).encode("utf-8")
            req = urllib.request.Request(
                f"{self.base_url}{path}",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, ConnectionRefusedError,
                OSError, json.JSONDecodeError, TimeoutError):
            return None

    @property
    def available(self) -> bool:
        return self._available

    @property
    def name(self) -> str:
        return "hindsight"

    # ── retain ─────────────────────────────────────────────

    def retain(self, content: str, context: str = "",
               tags: list = None, memory_type: str = "event") -> bool:
        if not self._available:
            return False

        tags = tags or []

        # Map our fields to Hindsight's retain format
        payload = {
            "document_id": f"{context}-{hash(content) % 10**8}",
            "content": content,
            "context": context or memory_type,
            "tags": tags,
            "bank": self.bank,
        }
        result = self._api_post("/retain", payload)
        return result is not None

    # ── recall ─────────────────────────────────────────────

    def recall(self, query: str, limit: int = 10) -> dict:
        if not self._available:
            return {"facts": [], "events": [], "narratives": [], "sessions": []}

        payload = {
            "query": query,
            "limit": limit,
            "bank": self.bank,
        }
        result = self._api_post("/recall", payload)

        if not result:
            return {"facts": [], "events": [], "narratives": [], "sessions": []}

        # Hindsight returns memories as a list; wrap in expected format
        memories = result.get("memories", [])
        return {
            "facts": [],
            "events": [{"id": i, "summary": m.get("content", ""),
                        "event_type": m.get("context", "recall"),
                        "tags": json.dumps(m.get("tags", [])),
                        "created_at": m.get("timestamp", "")}
                       for i, m in enumerate(memories)],
            "narratives": [],
            "sessions": [],
        }

    # ── reflect ────────────────────────────────────────────

    def reflect(self, question: str) -> dict:
        if not self._available:
            return {"question": question, "correction_patterns": [],
                    "relevant_insights": [], "relevant_facts": [],
                    "memory_count": 0}

        payload = {
            "query": question,
            "bank": self.bank,
        }
        result = self._api_post("/reflect", payload)

        if not result:
            return {"question": question, "correction_patterns": [],
                    "relevant_insights": [], "relevant_facts": [],
                    "memory_count": 0}

        # Hindsight returns a reflection string; wrap it
        reflection = result.get("reflection", "")
        return {
            "question": question,
            "correction_patterns": [{"summary": reflection}],
            "relevant_insights": [],
            "relevant_facts": [],
            "memory_count": 1 if reflection else 0,
        }

    # ── stats ──────────────────────────────────────────────

    def stats(self) -> dict:
        return {
            "backend": "hindsight",
            "base_url": self.base_url,
            "bank": self.bank,
            "available": self._available,
        }
