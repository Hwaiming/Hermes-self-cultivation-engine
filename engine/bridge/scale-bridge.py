#!/usr/bin/env python3
"""
Self-Cultivation Engine · SCALE Bridge

CLI gate that speaks SCALE Engine's hook protocol.
SCALE's PreToolUse / PostToolUse / beforeStop hooks
call this as an external command, receiving a SCALE-compatible
{decision, reason, suggestion, injectContext} response.

Usage:
  python3 scale-bridge.py pre-tool   --args-json '{"tool":"Edit","file_path":"..."}'
  python3 scale-bridge.py post-tool  --exit-code 0
  python3 scale-bridge.py stop

Protocol (SCALE-compatible stdout JSON):
  {"decision":"allow"|"block"|"deny","reason":"...","suggestion":"...","injectContext":[...]}

Exit codes (SCALE-compatible):
  0 = allow
  1 = block (soft, AI sees but doesn't halt)
  2 = deny  (hard, agent must stop)
"""
import sys
import json
import argparse
from pathlib import Path

# Add repo root to path (engine/ is a subdirectory)
_REPO_ROOT = Path(__file__).resolve().parents[2]  # bridge/engine/repo-root
sys.path.insert(0, str(_REPO_ROOT))

from engine.detectors.registry import get_registry
from engine.detectors.base import Severity, CheckResult
from engine.evidence.store import EvidenceStore, EvidenceRecord
from engine.hooks.runner import run_pre_flight
from engine.hooks.base import HookResult
from engine.fsm.runner import StateMachine


def make_response(decision="allow", reason="", suggestion="", inject_context=None):
    return {
        "decision": decision,
        "reason": reason,
        "suggestion": suggestion or None,
        "injectContext": inject_context or [],
    }


def exit_code(decision: str) -> int:
    return {"allow": 0, "block": 1, "deny": 2}.get(decision, 1)


def _msg(item):
    """Extract message from CheckResult, HookResult, or dict."""
    if isinstance(item, CheckResult):
        return item.message
    if isinstance(item, HookResult):
        return item.message
    if isinstance(item, dict):
        return item.get("message", str(item))
    return str(item)


def build_context(tool_name: str, args: dict, tool_type: str = "pre") -> dict:
    """Translate SCALE tool args into our detector context."""
    ctx = {"tool": tool_name, "tool_type": tool_type}
    if "output" in args:
        ctx["output"] = args["output"]
    if "exit_code" in args:
        ctx["exit_code"] = args["exit_code"]
    ctx["found_problem"] = tool_type == "pre" and args.get("found_problem", False)
    ctx["has_multiple_options"] = args.get("has_multiple_options", False)
    if tool_name in ("Edit", "Write", "MultiEdit", "Bash"):
        ctx["current_focus"] = f"{tool_name}:{args.get('file_path', '')}"
    if args.get("task_description"):
        ctx["task_id"] = args.get("task_id", f"scale_{tool_name}")
        ctx["original_scope"] = args.get("original_task", args.get("task_description"))
        ctx["current_scope"] = args.get("task_description")
    if tool_type == "post" and args.get("exit_code", 0) == 0:
        output = args.get("output", "")
        skip_patterns = ["environment issue", "env issue", "it should work", "skipping test"]
        ctx["has_skip_rationalization"] = any(p in output.lower() for p in skip_patterns)
    return ctx


# ── Gate Handlers ──────────────────────────────────────────

def handle_pre_tool(args: dict) -> dict:
    """PreToolUse: Run all detectors + hooks before the agent acts."""
    tool_name = args.get("tool", "unknown")
    tool_args = args.get("args_json", {})
    if isinstance(tool_args, str):
        try:
            tool_args = json.loads(tool_args)
        except json.JSONDecodeError:
            tool_args = {}

    ctx = build_context(tool_name, tool_args, tool_type="pre")
    results = get_registry().run_all(ctx)
    evidence_store = EvidenceStore()

    blocked = []
    warns = []

    for r in results:
        record = EvidenceRecord(
            check_type=f"scale_bridge.pre.{r.detector_name}",
            result=r.message, passed=r.passed,
            detail=json.dumps(r.to_dict(), ensure_ascii=False),
            context={"tool": tool_name, "args": tool_args},
        )
        evidence_store.save(record)
        if not r.passed:
            (blocked if r.severity in (Severity.BLOCK, Severity.DENY) else warns).append(r)

    # Run hooks (generate if needed)
    try:
        hook_results = run_pre_flight(ctx, auto_generate=True, quiet=True)
        for hr in hook_results:
            if not hr.passed:
                blocked.append(hr)
    except Exception:
        pass  # hooks are optional

    # Build SCALE response
    inject = []
    for w in warns:
        inject.append({"role": "system", "content": f"[self-cultivation] ⚠️ {_msg(w)}"})
    for b in blocked:
        inject.append({"role": "system", "content": f"[self-cultivation] ❌ {_msg(b)}"})

    if blocked:
        reasons = [_msg(b) for b in blocked]
        return make_response(
            decision="block",
            reason="; ".join(reasons[:3]),
            suggestion="Run `python3 -m engine.check` to inspect all detectors" if len(reasons) > 1 else None,
            inject_context=inject,
        )
    if warns:
        return make_response(
            decision="allow",
            reason=f"{len(warns)} warnings",
            inject_context=inject,
        )
    return make_response()


def handle_post_tool(args: dict) -> dict:
    """PostToolUse: Check for post-action patterns."""
    ctx = build_context(args.get("tool", "unknown"), {
        "exit_code": args.get("exit_code", 0),
        "output": args.get("output", ""),
    }, tool_type="post")

    results = get_registry().run_all(ctx)
    evidence_store = EvidenceStore()
    issues = []

    for r in results:
        record = EvidenceRecord(
            check_type=f"scale_bridge.post.{r.detector_name}",
            result=r.message, passed=r.passed,
            detail=json.dumps(r.to_dict(), ensure_ascii=False),
            context={"tool": args.get("tool"), "exit_code": args.get("exit_code")},
        )
        evidence_store.save(record)
        if not r.passed:
            issues.append(r)

    if issues:
        inject = [{"role": "system", "content": f"[self-cultivation] ⚠️ {_msg(i)}"} for i in issues]
        return make_response(decision="allow", reason=f"{len(issues)} post-action findings", inject_context=inject)
    return make_response()


def handle_stop(args: dict) -> dict:
    """BeforeStop: Check FSM state + detector status."""
    ctx = {}
    results = get_registry().run_all(ctx)
    fsm = StateMachine()
    state = fsm.current_state.value

    issues = [r for r in results if not r.passed]
    state_warning = ""
    if state == "corrected":
        state_warning = "Session ending while in CORRECTED state — correction cycle incomplete"
    elif state == "self_update":
        state_warning = "Session ending during SELF_UPDATE — update may be incomplete"
    elif state == "reflect":
        state_warning = "Session ending in REFLECT — ensure self file is updated"

    inject = []
    if state_warning:
        inject.append({"role": "system", "content": f"[self-cultivation] ⚠️ {state_warning}"})
    for issue in issues:
        inject.append({"role": "system", "content": f"[self-cultivation] ⚠️ {_msg(issue)}"})

    if state_warning:
        return make_response(
            decision="block" if state == "corrected" else "allow",
            reason=state_warning,
            suggestion="Complete the correction cycle before ending session" if state == "corrected" else None,
            inject_context=inject,
        )
    if issues:
        return make_response(decision="allow", reason=f"{len(issues)} pending issues", inject_context=inject)

    return make_response(
        decision="allow",
        inject_context=[{"role": "system", "content": "[self-cultivation] ✅ All behavioral checks clear"}],
    )


# ── Main ───────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="SCALE Bridge — Self-Cultivation Engine gate")
    parser.add_argument("gate", choices=["pre-tool", "post-tool", "stop"])
    parser.add_argument("--args-json", type=str, default="{}")
    parser.add_argument("--exit-code", type=int, default=0)
    parser.add_argument("--output", type=str, default="")
    parser.add_argument("--session-id", type=str, default="")

    args = parser.parse_args()
    parsed_args = args.__dict__
    if args.args_json:
        try:
            parsed_args.update(json.loads(args.args_json))
        except json.JSONDecodeError:
            pass

    handlers = {
        "pre-tool": handle_pre_tool,
        "post-tool": handle_post_tool,
        "stop": handle_stop,
    }
    response = handlers[args.gate](parsed_args)
    print(json.dumps(response, ensure_ascii=False, indent=2))
    sys.exit(exit_code(response["decision"]))


if __name__ == "__main__":
    main()
