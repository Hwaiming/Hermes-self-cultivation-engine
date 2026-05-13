"""
Self-Cultivation Engine · FSM Runner

Executes state transitions with guard checking, persistence, and evidence logging.

Usage:
    fsm = StateMachine()
    
    # Check if transition is possible
    result = fsm.can_transition(AgentState.NORMAL, AgentState.CORRECTED, context)
    if result["can_transition"]:
        fsm.transition_to(AgentState.CORRECTED, context)
    
    # Or attempt transition directly (raises TransitionError on guard failure)
    fsm.transition_to(AgentState.CORRECTED, context, strict=True)
    
    # Get current state
    print(fsm.current_state)  # AgentState.NORMAL
"""

import json
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone

from .states import (
    AgentState, TransitionError, TransitionGuard,
    find_transition, get_valid_transitions,
)
from ..evidence.store import EvidenceStore, EvidenceRecord


STATE_FILE = Path(__file__).parent / ".state.json"


class StateMachine:
    """
    Persistent state machine with guard-checked transitions.
    
    State is persisted to .state.json for cross-session continuity.
    Each transition attempt is logged as evidence with SHA-256.
    """
    
    def __init__(self, initial_state: AgentState = AgentState.NORMAL):
        self.evidence = EvidenceStore()
        self._state = self._load_state() or initial_state
    
    @property
    def current_state(self) -> AgentState:
        return self._state
    
    def _load_state(self) -> Optional[AgentState]:
        """Load persisted state from disk."""
        if STATE_FILE.exists():
            try:
                data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                return AgentState(data.get("state", "normal"))
            except (json.JSONDecodeError, ValueError):
                pass
        return None
    
    def _save_state(self):
        """Persist current state to disk."""
        STATE_FILE.write_text(json.dumps({
            "state": self._state.value,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False, indent=2), encoding="utf-8")
    
    def can_transition(self, target: AgentState, context: dict = None) -> dict:
        """
        Dry-run guard check: can we transition to target state?
        
        Returns:
            can_transition: bool
            guard_results: list[GuardResult]
            blocked_by: list[str]
        """
        ctx = context or {}
        transition = find_transition(self._state, target)
        
        if not transition:
            return {
                "can_transition": False,
                "guard_results": [],
                "blocked_by": [f"No valid transition from {self._state.value} to {target.value}"],
            }
        
        results = []
        blocked = []
        
        for guard in transition.guards:
            passed, reason = guard.evaluate(ctx)
            results.append({
                "guard": guard.name,
                "passed": passed,
                "reason": reason,
            })
            if not passed:
                blocked.append(guard.name)
        
        return {
            "can_transition": len(blocked) == 0,
            "guard_results": results,
            "blocked_by": blocked,
            "transition": {
                "from": self._state.value,
                "to": target.value,
                "description": transition.description,
            },
        }
    
    def transition_to(self, target: AgentState, context: dict = None, strict: bool = True) -> dict:
        """
        Attempt to transition to target state.
        
        If strict=True, raises TransitionError on guard failure.
        If strict=False, returns the can_transition result.
        Always saves evidence regardless of strict mode.
        """
        ctx = context or {}
        check = self.can_transition(target, ctx)
        
        # Log evidence
        record = EvidenceRecord(
            check_type=f"fsm.{self._state.value}_to_{target.value}",
            result=json.dumps(check, ensure_ascii=False),
            passed=check["can_transition"],
            detail=json.dumps({
                "from": self._state.value,
                "to": target.value,
                "blocked_by": check["blocked_by"],
            }, ensure_ascii=False),
        )
        self.evidence.save(record)
        
        if not check["can_transition"]:
            if strict:
                raise TransitionError(
                    from_state=self._state,
                    to_state=target,
                    guard_name=check["blocked_by"][0] if check["blocked_by"] else "unknown",
                    reason=f"Blocked by guards: {check['blocked_by']}",
                )
            return check
        
        # Execute transition
        old_state = self._state
        self._state = target
        self._save_state()
        
        check["executed"] = True
        check["previous_state"] = old_state.value
        return check
    
    def available_transitions(self, context: dict = None) -> list[dict]:
        """List all valid transitions from current state with guard status."""
        ctx = context or {}
        results = []
        
        for t in get_valid_transitions(self._state):
            check = self.can_transition(t.to_state, ctx)
            results.append({
                "to": t.to_state.value,
                "description": t.description,
                "can_transition": check["can_transition"],
                "blocked_by": check["blocked_by"],
                "guards": check["guard_results"],
            })
        
        return results
    
    def reset(self, target: AgentState = AgentState.NORMAL):
        """Force-reset state (bypasses guards). For maintenance use."""
        old = self._state
        self._state = target
        self._save_state()
        record = EvidenceRecord(
            check_type="fsm.force_reset",
            result=f"Force reset: {old.value} → {target.value}",
            passed=True,
        )
        self.evidence.save(record)


# CLI entry point
if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Self-Cultivation Engine · FSM")
    parser.add_argument("action", choices=["status", "available", "transition", "reset"],
                       help="Action to perform")
    parser.add_argument("--to", type=str, help="Target state for transition/reset")
    parser.add_argument("--context", type=str, help="JSON context file")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()
    
    fsm = StateMachine()
    
    if args.action == "status":
        result = {"state": fsm.current_state.value}
        if args.json:
            print(json.dumps(result, ensure_ascii=False))
        else:
            print(f"Current state: {result['state']}")
    
    elif args.action == "available":
        ctx = {}
        if args.context:
            with open(args.context) as f:
                ctx = json.load(f)
        result = fsm.available_transitions(ctx)
        if args.json:
            print(json.dumps(result, ensure_ascii=False))
        else:
            print(f"Available transitions from {fsm.current_state.value}:")
            for t in result:
                icon = "✅" if t["can_transition"] else "❌"
                print(f"  {icon} → {t['to']}: {t['description']}")
                if t["blocked_by"]:
                    print(f"       blocked by: {', '.join(t['blocked_by'])}")
    
    elif args.action == "transition":
        if not args.to:
            print("Error: --to required for transition")
            sys.exit(1)
        try:
            target = AgentState(args.to)
        except ValueError:
            print(f"Error: invalid state '{args.to}'. Valid: normal, corrected, self_update, reflect")
            sys.exit(1)
        
        ctx = {}
        if args.context:
            with open(args.context) as f:
                ctx = json.load(f)
        
        try:
            result = fsm.transition_to(target, ctx, strict=False)
            if args.json:
                print(json.dumps(result, ensure_ascii=False))
            elif result.get("can_transition"):
                print(f"✅ Transitioned: {result['previous_state']} → {target.value}")
            else:
                print(f"❌ Blocked by: {', '.join(result['blocked_by'])}")
        except TransitionError as e:
            print(f"❌ {e}")
            sys.exit(1)
    
    elif args.action == "reset":
        target = AgentState(args.to) if args.to else AgentState.NORMAL
        fsm.reset(target)
        print(f"Reset to {target.value}")
