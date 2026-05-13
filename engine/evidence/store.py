"""
Self-Cultivation Engine · Evidence Store

Persists verification evidence with SHA-256 content hashing.
Inspired by SCALE Engine's EvidenceStore pattern.

Each evidence record includes a SHA-256 hash of its content,
making tampering detectable.
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional


class EvidenceRecord:
    """A single verification/self-check evidence record."""
    
    def __init__(
        self,
        check_type: str,
        result: str,
        passed: bool,
        source: str = "",
        detail: str = "",
        context: Optional[dict] = None,
    ):
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.check_type = check_type
        self.result = result
        self.passed = passed
        self.source = source
        self.detail = detail
        self.context = context or {}
        self._hash = self._compute_hash()
    
    def _compute_hash(self) -> str:
        content = json.dumps({
            "timestamp": self.timestamp,
            "check_type": self.check_type,
            "result": self.result,
            "passed": self.passed,
            "source": self.source,
            "detail": self.detail,
        }, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(content.encode()).hexdigest()
    
    @property
    def sha256(self) -> str:
        return self._hash
    
    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "check_type": self.check_type,
            "result": self.result,
            "passed": self.passed,
            "source": self.source,
            "detail": self.detail,
            "sha256": self._hash,
        }


class EvidenceStore:
    """
    Persistence for verification evidence.
    
    Each record is stored as a JSON file with SHA-256 content hash.
    Naming: EVIDENCE-{check_type}-{timestamp}.json
    
    Usage:
        store = EvidenceStore(".scale/evidence")
        record = EvidenceRecord("self_check", "All clear", True)
        store.save(record)
        
        records = store.list_recent(limit=10)
    """
    
    def __init__(self, base_path: str = ".scale/evidence"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def save(self, record: EvidenceRecord) -> str:
        """Save an evidence record. Returns the file path."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        safe_type = record.check_type.replace("/", "_").replace(" ", "_")
        filename = f"EVIDENCE-{safe_type}-{timestamp}.json"
        filepath = self.base_path / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(record.to_dict(), f, ensure_ascii=False, indent=2)
        
        return str(filepath)
    
    def verify(self, filepath: str) -> bool:
        """Verify that a record's content matches its SHA-256 hash."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            stored_hash = data.pop("sha256", "")
            content = json.dumps(data, sort_keys=True, ensure_ascii=False)
            computed_hash = hashlib.sha256(content.encode()).hexdigest()
            
            return computed_hash == stored_hash
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return False
    
    def list_recent(self, limit: int = 20) -> list[dict]:
        """List recent evidence records, newest first."""
        files = sorted(self.base_path.glob("EVIDENCE-*.json"), reverse=True)
        records = []
        for f in files[:limit]:
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                data["_file"] = str(f)
                data["_verified"] = self._quick_verify(data)
                records.append(data)
            except (json.JSONDecodeError, IOError):
                pass
        return records
    
    def _quick_verify(self, data: dict) -> bool:
        """In-memory hash verification. Recomputes hash over non-sha256 fields."""
        stored_hash = data.get("sha256", "")
        if not stored_hash:
            return False
        # Reconstruct original content (the 6 fields that were hashed)
        content = json.dumps({
            "timestamp": data.get("timestamp", ""),
            "check_type": data.get("check_type", ""),
            "result": data.get("result", ""),
            "passed": data.get("passed", False),
            "source": data.get("source", ""),
            "detail": data.get("detail", ""),
        }, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(content.encode()).hexdigest() == stored_hash
    
    def get(self, filepath: str) -> Optional[dict]:
        """Get a single record by filepath."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["_file"] = str(filepath)
            data["_verified"] = self._quick_verify(data)
            return data
        except (FileNotFoundError, json.JSONDecodeError):
            return None
    
    def summary(self) -> dict:
        """Get a summary of all evidence records."""
        records = self.list_recent(limit=1000)
        return {
            "total": len(records),
            "passed": sum(1 for r in records if r.get("passed", False)),
            "failed": sum(1 for r in records if not r.get("passed", True)),
            "verified": sum(1 for r in records if r.get("_verified", False)),
            "tampered": sum(1 for r in records if not r.get("_verified", True)),
            "check_types": {},
        }
