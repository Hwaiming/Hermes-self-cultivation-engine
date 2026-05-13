"""
Detector: Scope Creep — Task scope expanding beyond original boundaries.

Triggers when the current task description or scope grows
significantly beyond the original intent.

Uses persistent state in .scale/scopecreeps/history.json
Tracks the original scope definition and each update.
"""
import json
import time
import re
from pathlib import Path

from .base import BaseDetector, Severity, CheckResult, EvidenceItem


# ── Persistent State ───────────────────────────────────────

_BASE = Path(__file__).resolve().parent.parent / ".scale" / "scopecreeps"
_HISTORY_FILE = _BASE / "scopes.json"

SCOPES_DEFAULT = {
    "tasks": [],         # list of {"id": str, "scope": str, "original": str, "timestamp": float, "updates": int}
}


def _load_scopes() -> dict:
    _BASE.mkdir(parents=True, exist_ok=True)
    if _HISTORY_FILE.exists():
        try:
            return json.loads(_HISTORY_FILE.read_text())
        except (json.JSONDecodeError, ValueError):
            pass
    return dict(SCOPES_DEFAULT)


def _save_scopes(data: dict):
    _BASE.mkdir(parents=True, exist_ok=True)
    _HISTORY_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))


# ── Detection Logic ────────────────────────────────────────

# Expansion-related keywords — not always scope creep,
# but an increasing ratio suggests scope drift.
_EXPANSION_KEYWORDS = [
    "also", "adding", "additionally", "plus", "extra",
    "in addition", "while we're", "another thing",
    "顺便", "另外", "再加", "顺便加", "额外",
]

_STOP_PHRASES = [
    "out of scope", "wontfix", "won't fix", "not now",
    "先不", "暂时不", "下次",
]


def _count_expansion_markers(text: str) -> int:
    """Count how many scope-expansion markers appear in text."""
    text_lower = text.lower()
    count = 0
    for kw in _EXPANSION_KEYWORDS:
        count += text_lower.count(kw)
    return count


def _has_stop_phrases(text: str) -> bool:
    """Check if any stop/constraint phrases are present."""
    text_lower = text.lower()
    return any(sp in text_lower for sp in _STOP_PHRASES)


def _compute_expansion_ratio(current: str, original: str) -> float:
    """
    Estimate scope expansion ratio based on word count.
    A ratio > 1.5x suggests meaningful creep.
    """
    current_words = len(re.findall(r'\w+', current))
    original_words = len(re.findall(r'\w+', original))
    if original_words == 0:
        return 1.0
    return current_words / original_words


def _compute_keyword_delta(current: str, original: str) -> int:
    """Extra expansion keywords beyond original description."""
    return _count_expansion_markers(current) - _count_expansion_markers(original)


# ── Detector ────────────────────────────────────────────────

class ScopeCreepDetector(BaseDetector):
    """
    Detects when a task's scope expands beyond its original definition.

    Context fields:
      task_id: str — unique identifier for this task (e.g. 'fix_auth_flow')
      original_scope: str — the initial task description/scope
      current_scope: str — the current (potentially expanded) scope
      has_stop_phrases: bool — optional, if user explicitly constrained scope

    Detection conditions:
      1. Expansion ratio (word count current / word count original) > 2.0 → BLOCK
      2. Expansion ratio > 1.5 AND 2+ expansion markers added → WARN
      3. Same task updated 4+ times → WARN (churn indicator)
      4. Stop phrases present → skip (user explicitly constrained)
    """
    name = "scope_creep"
    description = "Detects when task scope expands beyond original boundaries"
    severity = Severity.BLOCK
    CREEP_RATIO_HARD = 2.0      # Hard block
    CREEP_RATIO_WARN = 1.5      # Soft warn
    KEYWORD_DELTA_WARN = 2      # Additional expansion markers
    MAX_UPDATES = 4             # Max scope updates before warn

    def check(self, context: dict = None) -> CheckResult:
        ctx = context or {}
        task_id = ctx.get("task_id", "")
        original_scope = ctx.get("original_scope", "")
        current_scope = ctx.get("current_scope", "")
        has_stop_phrases = ctx.get("has_stop_phrases", False)

        # Need both scopes to compare
        if not original_scope or not current_scope:
            return self.passed("Need both original_scope and current_scope")

        # If stop phrases present, user already constrained scope — skip
        if has_stop_phrases or _has_stop_phrases(current_scope):
            return self.passed("Scope is explicitly constrained — skipping creep check")

        # Load persistent state
        scopes = _load_scopes()
        tasks = scopes.get("tasks", [])

        # Find or create task entry
        task_entry = None
        for t in tasks:
            if t.get("id") == task_id:
                task_entry = t
                break

        if task_entry is None:
            # First scope registration for this task
            task_entry = {
                "id": task_id,
                "scope": current_scope,
                "original": original_scope,
                "timestamp": time.time(),
                "updates": 0,
            }
            tasks.append(task_entry)
            _save_scopes(scopes)
            return self.passed("Initial scope registered — no creep yet")

        # ── Existing task: check for creep ──

        # Increment update counter
        task_entry["updates"] += 1

        # Compute metrics
        ratio = _compute_expansion_ratio(current_scope, task_entry["original"])
        keyword_delta = _compute_keyword_delta(current_scope, original_scope)
        total_updates = task_entry["updates"]

        # ── Condition 1: Hard block (ratio > 2.0) ──
        if ratio >= self.CREEP_RATIO_HARD:
            evidence = [
                EvidenceItem(
                    kind="pattern_match",
                    description=f"Scope expanded {ratio:.1f}x beyond original",
                    value=ratio,
                    threshold=self.CREEP_RATIO_HARD,
                ),
                EvidenceItem(
                    kind="event_count",
                    description=f"Update count: {total_updates}, keyword delta: +{keyword_delta}",
                    value=float(total_updates),
                ),
            ]
            return CheckResult(
                detector_name=self.name,
                severity=Severity.BLOCK,
                passed=False,
                message=f"Scope creep ({ratio:.1f}x): '{task_id}' expanded beyond {self.CREEP_RATIO_HARD}x original scope",
                evidence=evidence,
            )

        # ── Condition 2: Warn (ratio > 1.5 AND keyword delta >= 2) ──
        if ratio >= self.CREEP_RATIO_WARN and keyword_delta >= self.KEYWORD_DELTA_WARN:
            evidence = [
                EvidenceItem(
                    kind="pattern_match",
                    description=f"Scope expanded {ratio:.1f}x with +{keyword_delta} expansion markers",
                    value=ratio,
                    threshold=self.CREEP_RATIO_WARN,
                ),
            ]
            return CheckResult(
                detector_name=self.name,
                severity=Severity.WARN,
                passed=False,
                message=f"Scope creep warning: '{task_id}' expanded {ratio:.1f}x with {keyword_delta}+ expansion markers",
                evidence=evidence,
            )

        # ── Condition 3: Churn indicator (4+ updates) ──
        if total_updates >= self.MAX_UPDATES:
            evidence = [
                EvidenceItem(
                    kind="event_count",
                    description=f"Scope redefined {total_updates} times",
                    value=float(total_updates),
                    threshold=float(self.MAX_UPDATES),
                ),
            ]
            return CheckResult(
                detector_name=self.name,
                severity=Severity.WARN,
                passed=False,
                message=f"Scope churn: '{task_id}' redefined {total_updates}x (threshold: {self.MAX_UPDATES})",
                evidence=evidence,
            )

        # ── Update scope for next check ──
        task_entry["scope"] = current_scope
        task_entry["timestamp"] = time.time()
        _save_scopes(scopes)

        return self.passed()


    @classmethod
    def reset(cls):
        """Clear all tracked scopes."""
        _save_scopes(dict(SCOPES_DEFAULT))


    @classmethod
    def status(cls) -> dict:
        """Current scope tracking for debugging."""
        scopes = _load_scopes()
        return {
            "tasks": scopes.get("tasks", []),
            "total": len(scopes.get("tasks", [])),
        }
