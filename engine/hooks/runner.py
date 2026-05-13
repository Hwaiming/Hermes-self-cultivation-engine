"""
Self-Cultivation Engine · Hook Runner

Runs all generated hooks, aggregates results, and determines
whether the action should proceed.

Can be used as:
1. CLI pre-flight check: python3 -m engine.hooks.runner
2. Python import: runner.run_all(context)
3. Integration with execution-procedures skill
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone

# Add parent to path for standalone execution
_ENGINE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ENGINE_DIR))

from engine.hooks.base import HookResult, HookSeverity, HookType
from engine.hooks.generator import generate_all_hooks
from engine.evidence.store import EvidenceStore, EvidenceRecord


HOOKS_DIR = Path(__file__).parent / "generated"


class HookRunner:
    """
    Runs all generated hooks and aggregates results.
    
    Usage:
        runner = HookRunner()
        results = runner.run_all({"output": "...", "was_corrected": True})
        
        if runner.should_block(results):
            print("BLOCKED by hook")
        else:
            print("All clear")
    """
    
    def __init__(self):
        self.evidence = EvidenceStore()
    
    def run_all(self, context: Optional[dict] = None) -> list[HookResult]:
        """Run all generated hooks and return results."""
        if not HOOKS_DIR.exists():
            return []
        
        hooks = sorted(HOOKS_DIR.glob("*.py"))
        results = []
        
        for hook_path in hooks:
            result = self._run_hook(hook_path, context)
            results.append(result)
            
            # Save evidence
            record = EvidenceRecord(
                check_type=f"hook.{result.hook_name}",
                result=result.message,
                passed=result.passed,
                detail=json.dumps({
                    "hook_name": result.hook_name,
                    "severity": result.severity.value,
                    "exit_code": result.exit_code,
                }, ensure_ascii=False),
            )
            evidence_path = self.evidence.save(record)
            result.evidence_file = evidence_path
        
        return results
    
    def _run_hook(self, hook_path: Path, context: Optional[dict] = None) -> HookResult:
        """Run a single hook script."""
        hook_name = hook_path.stem
        
        try:
            ctx_json = json.dumps(context or {}, ensure_ascii=False)
            result = subprocess.run(
                [sys.executable, str(hook_path), ctx_json],
                capture_output=True, text=True, timeout=10,
            )
            
            output = result.stdout.strip()
            if output:
                data = json.loads(output)
                return HookResult(
                    hook_name=data.get("hook_name", hook_name),
                    severity=HookSeverity(data.get("severity", "warn")),
                    passed=data.get("passed", True),
                    message=data.get("message", ""),
                    exit_code=result.returncode,
                )
            
            return HookResult(
                hook_name=hook_name,
                severity=HookSeverity.WARN,
                passed=result.returncode == 0,
                message=f"Hook returned no output (exit: {result.returncode})",
                exit_code=result.returncode,
            )
            
        except subprocess.TimeoutExpired:
            return HookResult(
                hook_name=hook_name,
                severity=HookSeverity.WARN,
                passed=False,
                message="Hook timed out (10s)",
                exit_code=-1,
            )
        except (json.JSONDecodeError, FileNotFoundError) as e:
            return HookResult(
                hook_name=hook_name,
                severity=HookSeverity.WARN,
                passed=True,
                message=f"Hook error: {e}",
                exit_code=0,
            )
    
    def should_block(self, results: list[HookResult]) -> bool:
        """Check if any BLOCK-severity hook failed."""
        return any(
            r.severity == HookSeverity.BLOCK and not r.passed
            for r in results
        )
    
    def summary(self, results: list[HookResult]) -> dict:
        """Aggregate hook results."""
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        blocked = sum(1 for r in results if r.severity == HookSeverity.BLOCK and not r.passed)
        warned = sum(1 for r in results if r.severity == HookSeverity.WARN and not r.passed)
        
        return {
            "total": total,
            "passed": passed,
            "blocked": blocked,
            "warned": warned,
            "can_proceed": not any(
                r.severity == HookSeverity.BLOCK and not r.passed
                for r in results
            ),
        }


def run_pre_flight(context: Optional[dict] = None, auto_generate: bool = True, quiet: bool = True) -> list[HookResult]:
    """
    Pre-flight check: auto-generate hooks if needed, then run all.
    """
    if auto_generate:
        generate_all_hooks(quiet=quiet)
    
    runner = HookRunner()
    results = runner.run_all(context)
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Self-Cultivation Engine · Hook Runner")
    parser.add_argument("--context", type=str, help="JSON context file")
    parser.add_argument("--generate-only", action="store_true", help="Generate hooks, don't run")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()
    
    if args.generate_only:
        generated = generate_all_hooks()
        if args.json:
            print(json.dumps({"generated": len(generated), "hooks": generated}, ensure_ascii=False))
        else:
            print(f"Generated {len(generated)} hooks")
        sys.exit(0)
    
    # Load context
    context = {}
    if args.context:
        try:
            with open(args.context, "r") as f:
                context = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading context: {e}")
            sys.exit(1)
    
    # Auto-generate + run
    generate_all_hooks(quiet=True)
    results = run_pre_flight(context, auto_generate=False)
    summary = HookRunner().summary(results)
    
    if args.json:
        output = {
            "summary": summary,
            "results": [
                {
                    "hook_name": r.hook_name,
                    "severity": r.severity.value,
                    "passed": r.passed,
                    "message": r.message,
                    "evidence_file": r.evidence_file,
                }
                for r in results
            ],
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"  Pre-Flight Hook Check")
        print(f"{'='*60}")
        print(f"  Hooks: {summary['total']} | ✅ {summary['passed']} | 🛑 {summary['blocked']} blocked | ⚠️  {summary['warned']} warned")
        
        if not summary["can_proceed"]:
            print(f"\n  🔴 BLOCKED — cannot proceed until hooks pass")
        else:
            print(f"\n  🟢 All clear — can proceed")
        
        print()
        for r in results:
            icon = "✅" if r.passed else "❌"
            sev_icon = {"block": "🛑", "warn": "⚠️", "info": "ℹ️"}.get(r.severity.value, "○")
            print(f"  {icon}{sev_icon} {r.hook_name}")
            if not r.passed:
                print(f"       {r.message}")
            if r.evidence_file:
                print(f"       {r.evidence_file}")
        print(f"{'='*60}\n")
    
    sys.exit(0 if summary["can_proceed"] else 1)
