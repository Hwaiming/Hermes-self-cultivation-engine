"""
Self-Cultivation Engine · FSM States & Transitions

Four states, each with guard functions that must pass before transition.

State machine:
```
                  ┌─────────────────────────────────────┐
                  │                  ┌──────────┐       │
                  │  cron & stale    │SELF-UPDATE│       │
                  │  ┌──────────────>│           │       │
                  │  │               └─────┬─────┘       │
                  │  │                     │             │
                  │  │              update_complete      │
                  │  │                     │             │
    ┌─────────┐   │  │                     ▼             │
    │ NORMAL  │───┘  │                                  │
    │         │───────┘  was_corrected                  │
    └────┬────┘                                         │
         │              ┌──────────┐                     │
         │              │CORRECTED │                     │
         └─────────────>│          │─────────────────────┘
          was_corrected  └──────────┘  error_log + narrative
                              │
                              │  conversation_ending
                              ▼
                         ┌─────────┐
                         │ REFLECT │
                         │         │
                         └────┬────┘
                              │
                              │  self_file_updated
                              ▼
                          NORMAL (loop)
```

Guards ensure transitions only happen when preconditions are met.
If a guard fails, the transition is blocked and evidence is recorded.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Callable, Optional
from datetime import datetime, timezone


class AgentState(Enum):
    NORMAL = "normal"
    CORRECTED = "corrected"
    SELF_UPDATE = "self_update"
    REFLECT = "reflect"


class TransitionError(Exception):
    """Raised when a guarded transition fails."""
    def __init__(self, from_state: AgentState, to_state: AgentState, 
                 guard_name: str, reason: str):
        self.from_state = from_state
        self.to_state = to_state
        self.guard_name = guard_name
        self.reason = reason
        super().__init__(f"{from_state.value}→{to_state.value} BLOCKED by {guard_name}: {reason}")


@dataclass
class TransitionGuard:
    """A single guard on a state transition."""
    name: str
    check: Callable[[dict], bool]
    fail_message: str = ""
    
    def evaluate(self, context: dict) -> tuple[bool, str]:
        """Run guard. Returns (passed, reason)."""
        try:
            passed = self.check(context)
            return passed, "" if passed else (self.fail_message or f"Guard '{self.name}' failed")
        except Exception as e:
            return False, f"Guard '{self.name}' error: {e}"


@dataclass
class Transition:
    """A valid state transition with guards."""
    from_state: AgentState
    to_state: AgentState
    description: str
    guards: list[TransitionGuard] = field(default_factory=list)


# ─── Guard Functions ──────────────────────────────────────

def guard_was_corrected(context: dict) -> bool:
    """Only transition to CORRECTED if user actually corrected us."""
    return context.get("was_corrected", False)


def guard_error_log_updated(context: dict) -> bool:
    """Cannot leave CORRECTED without updating the error log."""
    return context.get("error_log_updated", False)


def guard_narrative_appended(context: dict) -> bool:
    """Cannot leave CORRECTED without appending narrative."""
    return context.get("narrative_appended", False)


def guard_cron_triggered(context: dict) -> bool:
    """Only enter SELF_UPDATE via cron or explicit trigger."""
    return context.get("cron_triggered", False) or context.get("force_self_update", False)


def guard_session_stale(context: dict) -> bool:
    """Check if self file hasn't been updated recently."""
    last_update = context.get("last_self_update_days", 0)
    return last_update >= 1 or context.get("force_self_update", False)


def guard_update_complete(context: dict) -> bool:
    """Check that self-update actually produced output."""
    return context.get("update_completed", False)


def guard_conversation_ending(context: dict) -> bool:
    """Only enter REFLECT at conversation end."""
    return context.get("conversation_ending", False)


def guard_self_file_updated(context: dict) -> bool:
    """Cannot leave REFLECT without updating the self file."""
    return context.get("self_file_updated", False)


# ─── Transition Table ─────────────────────────────────────

TRANSITIONS: list[Transition] = [
    # NORMAL → CORRECTED
    Transition(
        from_state=AgentState.NORMAL,
        to_state=AgentState.CORRECTED,
        description="User correction triggered",
        guards=[
            TransitionGuard(
                name="was_corrected",
                check=guard_was_corrected,
                fail_message="No correction detected — cannot enter CORRECTED state",
            ),
        ],
    ),
    # NORMAL → SELF_UPDATE
    Transition(
        from_state=AgentState.NORMAL,
        to_state=AgentState.SELF_UPDATE,
        description="Cron-triggered self-update",
        guards=[
            TransitionGuard(
                name="cron_triggered",
                check=guard_cron_triggered,
                fail_message="Not cron-triggered — cannot enter SELF_UPDATE state",
            ),
            TransitionGuard(
                name="session_stale",
                check=guard_session_stale,
                fail_message="Session is fresh — no update needed",
            ),
        ],
    ),
    # CORRECTED → NORMAL
    Transition(
        from_state=AgentState.CORRECTED,
        to_state=AgentState.NORMAL,
        description="Correction processed and logged",
        guards=[
            TransitionGuard(
                name="error_log_updated",
                check=guard_error_log_updated,
                fail_message="Error log not updated — cannot leave CORRECTED state",
            ),
            TransitionGuard(
                name="narrative_appended",
                check=guard_narrative_appended,
                fail_message="Narrative not appended — cannot leave CORRECTED state",
            ),
        ],
    ),
    # CORRECTED → REFLECT
    Transition(
        from_state=AgentState.CORRECTED,
        to_state=AgentState.REFLECT,
        description="Conversation ending after correction",
        guards=[
            TransitionGuard(
                name="conversation_ending",
                check=guard_conversation_ending,
                fail_message="Conversation not ending — use CORRECTED→NORMAL instead",
            ),
        ],
    ),
    # SELF_UPDATE → NORMAL
    Transition(
        from_state=AgentState.SELF_UPDATE,
        to_state=AgentState.NORMAL,
        description="Self-update completed",
        guards=[
            TransitionGuard(
                name="update_complete",
                check=guard_update_complete,
                fail_message="Self-update not complete — cannot leave SELF_UPDATE state",
            ),
        ],
    ),
    # NORMAL → REFLECT
    Transition(
        from_state=AgentState.NORMAL,
        to_state=AgentState.REFLECT,
        description="Conversation ending in normal state",
        guards=[
            TransitionGuard(
                name="conversation_ending",
                check=guard_conversation_ending,
                fail_message="Conversation not ending — stay in NORMAL",
            ),
        ],
    ),
    # REFLECT → NORMAL
    Transition(
        from_state=AgentState.REFLECT,
        to_state=AgentState.NORMAL,
        description="Reflection complete, self file updated",
        guards=[
            TransitionGuard(
                name="self_file_updated",
                check=guard_self_file_updated,
                fail_message="Self file not updated — cannot leave REFLECT state",
            ),
        ],
    ),
]


def find_transition(from_state: AgentState, to_state: AgentState) -> Optional[Transition]:
    """Find a valid transition between two states."""
    for t in TRANSITIONS:
        if t.from_state == from_state and t.to_state == to_state:
            return t
    return None


def get_valid_transitions(from_state: AgentState) -> list[Transition]:
    """Get all valid transitions from a given state."""
    return [t for t in TRANSITIONS if t.from_state == from_state]
