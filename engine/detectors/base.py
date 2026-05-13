"""
Self-Cultivation Engine · Base Detector

All detectors inherit from this base class.
Each detector checks for ONE specific behavioral pattern
and returns a CheckResult with severity + evidence.
"""

from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Optional
import hashlib
import json
from datetime import datetime, timezone


class Severity(Enum):
    WARN = "warn"      # Informational, injected into context
    BLOCK = "block"    # Blocks action, agent must explain
    DENY = "deny"      # Hard block, human intervention required


@dataclass
class EvidenceItem:
    """A single piece of evidence for a detector finding."""
    kind: str            # 'pattern_match' | 'event_count' | 'time_window' | 'regex_match'
    description: str     # Human-readable description
    detail: str = ""     # Machine-readable detail (e.g., matched text)
    value: float = 0.0   # Numeric value (e.g., match count, duration)
    threshold: float = 0.0  # Threshold that was exceeded


@dataclass
class CheckResult:
    """Result of running a detector check."""
    detector_name: str
    severity: Severity
    passed: bool                # True = no issue, False = issue detected
    message: str                # Human-readable summary
    evidence: list[EvidenceItem] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "detector": self.detector_name,
            "severity": self.severity.value,
            "passed": self.passed,
            "message": self.message,
            "evidence": [asdict(e) for e in self.evidence],
        }
    
    @property
    def sha256(self) -> str:
        """Content-addressed hash of this result."""
        raw = json.dumps(self.to_dict(), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode()).hexdigest()


class BaseDetector:
    """
    Base class for all detectors.

    Subclasses must implement:
    - name: str (class variable)
    - check() -> CheckResult
    """
    name: str = "base"
    description: str = ""
    severity: Severity = Severity.WARN
    
    def check(self, context: Optional[dict] = None) -> CheckResult:
        """Run this detector. Override in subclass."""
        raise NotImplementedError
    
    def passed(self, message: str = "", evidence: list = None) -> CheckResult:
        return CheckResult(
            detector_name=self.name,
            severity=self.severity,
            passed=True,
            message=message or "No issue detected",
            evidence=evidence or [],
        )
    
    def failed(self, message: str, evidence: list = None) -> CheckResult:
        return CheckResult(
            detector_name=self.name,
            severity=self.severity,
            passed=False,
            message=message,
            evidence=evidence or [],
        )
