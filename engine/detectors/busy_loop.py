"""
Detector: Busy Loop — Same focus repeated without progress.

Triggers when the agent works on the same topic/action/task
multiple times in a row without making forward progress.

Uses persistent state in .scale/busyloops/history.json
"""
import json
import time
from pathlib import Path

from .base import BaseDetector, Severity, CheckResult, EvidenceItem


# ── Persistent State ───────────────────────────────────────

_BASE = Path(__file__).resolve().parent.parent / ".scale" / "busyloops"
_HISTORY_FILE = _BASE / "history.json"

BUSYLOOP_HISTORY_DEFAULT = {
    "entries": [],        # list of {"focus": str, "timestamp": float}
    "last_non_repeat": 0,  # index of last non-repeat entry
}


def _load_history() -> dict:
    _BASE.mkdir(parents=True, exist_ok=True)
    if _HISTORY_FILE.exists():
        try:
            return json.loads(_HISTORY_FILE.read_text())
        except (json.JSONDecodeError, ValueError):
            pass
    return dict(BUSYLOOP_HISTORY_DEFAULT)


def _save_history(data: dict):
    _BASE.mkdir(parents=True, exist_ok=True)
    _HISTORY_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))


# ── Detector ────────────────────────────────────────────────

class BusyLoopDetector(BaseDetector):
    """
    Detects repetitive focus on the same topic/action.

    Context fields:
      current_focus: str — a short label for what the agent is doing now
        (e.g. 'fix_null_pointer', 'choose_api_provider', 'debug_auth_flow')

    The detector maintains a rolling history of up to 10 entries.
    If the same focus appears 3+ times consecutively → BLOCK.
    If 3+ times with at most 1 different focus between them → WARN.
    """
    name = "busy_loop"
    description = "Detects repetitive focus on the same topic without progress"
    severity = Severity.BLOCK
    MAX_HISTORY = 10
    REPEAT_THRESHOLD = 3  # consecutive or near-consecutive repeats

    def check(self, context: dict = None) -> CheckResult:
        ctx = context or {}
        current_focus = ctx.get("current_focus", "")

        if not current_focus:
            return self.passed("No focus provided — skipping busy loop check")

        current_focus = current_focus.strip().lower()

        # Load history, append current, trim
        history = _load_history()
        entries = history.get("entries", [])
        last_non_repeat = history.get("last_non_repeat", len(entries))

        entries.append({
            "focus": current_focus,
            "timestamp": time.time(),
        })
        if len(entries) > self.MAX_HISTORY:
            entries.pop(0)

        # Analyse: count consecutive repeats from the end
        repeats = 0
        for entry in reversed(entries):
            if entry["focus"] == current_focus:
                repeats += 1
            else:
                break

        # Near-consecutive: scan whole history for this focus
        total_in_history = sum(1 for e in entries if e["focus"] == current_focus)
        unique_in_history = len(set(e["focus"] for e in entries))

        # Save updated history
        history["entries"] = entries
        history["last_non_repeat"] = last_non_repeat
        _save_history(history)

        # ── Consecutive repeat check (hard block) ──
        if repeats >= self.REPEAT_THRESHOLD:
            evidence = [
                EvidenceItem(
                    kind="event_count",
                    description=f"Same focus '{current_focus}' repeated {repeats} times consecutively",
                    value=float(repeats),
                    threshold=float(self.REPEAT_THRESHOLD),
                ),
                EvidenceItem(
                    kind="pattern_match",
                    description=f"History size: {len(entries)}, total hits for this focus: {total_in_history}",
                    value=float(total_in_history),
                ),
            ]
            return self.failed(
                f"Busy loop detected: '{current_focus}' repeated {repeats}x consecutively (threshold: {self.REPEAT_THRESHOLD})",
                evidence=evidence,
            )

        # ── High-frequency check (warn) ──
        if total_in_history >= self.REPEAT_THRESHOLD and unique_in_history <= 2:
            evidence = [
                EvidenceItem(
                    kind="event_count",
                    description=f"Focus '{current_focus}' appears {total_in_history}/{len(entries)} times, only {unique_in_history} unique topics",
                    value=float(total_in_history),
                    threshold=float(self.REPEAT_THRESHOLD),
                ),
            ]
            return CheckResult(
                detector_name=self.name,
                severity=Severity.WARN,
                passed=False,
                message=f"Potential busy loop: '{current_focus}' appears {total_in_history}/{len(entries)} history entries",
                evidence=evidence,
            )

        return self.passed()


    @classmethod
    def reset(cls):
        """Clear the busy loop history."""
        _save_history(dict(BUSYLOOP_HISTORY_DEFAULT))


    @classmethod
    def status(cls) -> dict:
        """Current history for debugging."""
        history = _load_history()
        return {
            "entries": history.get("entries", []),
            "total": len(history.get("entries", [])),
        }
