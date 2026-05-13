"""
Hermes Memory System · Narrative Log

Append-only story-first memory. Each entry is a short scene
with a transformation, not an attribute list.

Paired with the Narrative-First Update principle from
the Self-Cultivation Engine's three-principles.md.
"""
import json
import time
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone


class NarrativeLog:
    """Append-only narrative log. Each entry is a structured scene.

    Format:
    ```json
    {
        "timestamp": "2026-05-13T10:00:00+00:00",
        "session_id": "abc123",
        "type": "correction" | "insight" | "decision" | "reflection",
        "scene": "Kuroro pointed out I was fusing two concepts...",
        "transformation": "Now I check original sources before merging",
        "tags": ["concept_fusion", "correction"]
    }
    ```
    """

    def __init__(self, log_path: str = ""):
        if not log_path:
            log_path = str(Path(__file__).resolve().parent.parent / ".scale" / "narrative.jsonl")
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, session_id: str, entry_type: str, scene: str,
               transformation: str = "", tags: list = None) -> bool:
        """Write one narrative entry (append-only)."""
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
            "type": entry_type,
            "scene": scene,
            "transformation": transformation,
            "tags": tags or [],
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return True

    def read_recent(self, limit: int = 20) -> list[dict]:
        """Read most recent entries."""
        if not self.log_path.exists():
            return []
        entries = []
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return entries[-limit:]

    def search(self, keyword: str, limit: int = 20) -> list[dict]:
        """Simple keyword match across narrative entries."""
        if not self.log_path.exists():
            return []
        keyword_lower = keyword.lower()
        matches = []
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if (keyword_lower in entry.get("scene", "").lower()
                            or keyword_lower in entry.get("transformation", "").lower()
                            or keyword_lower in " ".join(entry.get("tags", [])).lower()):
                        matches.append(entry)
                except json.JSONDecodeError:
                    pass
        return matches[-limit:]

    def count(self) -> int:
        """Total entries in the log."""
        if not self.log_path.exists():
            return 0
        count = 0
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    count += 1
        return count

    def stats(self) -> dict:
        """Narrative log statistics."""
        return {
            "path": str(self.log_path),
            "entries": self.count(),
            "exists": self.log_path.exists(),
        }
