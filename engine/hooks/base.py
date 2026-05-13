"""
Self-Cultivation Engine · Hook System

Hooks are executable pre-flight checks auto-generated from
the error-pattern-registry when patterns reach safety_rule level.

Unlike SOUL.md text rules, hooks physically block or warn
before a tool call executes.

Architecture:
  BaseHook        → abstract interface
  HookGenerator   → reads pattern registry → generates hooks
  HookRunner      → executes hooks, aggregates results
  Generated hooks → standalone Python scripts in hooks/generated/
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path


class HookType(Enum):
    PRE_TOOL = "pre_tool"     # Run before tool call, can block
    POST_TOOL = "post_tool"   # Run after tool call, audit only
    PRE_FLIGHT = "pre_flight" # Run before any action (general)


class HookSeverity(Enum):
    BLOCK = "block"  # Exit code 1 — physically blocks
    WARN = "warn"    # Exit code 0 — warns but allows
    INFO = "info"    # Exit code 0 — informational only


@dataclass
class HookResult:
    """Result of running a hook."""
    hook_name: str
    severity: HookSeverity
    passed: bool
    message: str = ""
    evidence_file: str = ""
    exit_code: int = 0


class BaseHook:
    """
    Base class for all hooks.
    
    Hooks are Python callables that receive context and return a verdict.
    They can be auto-generated from pattern registry entries.
    """
    
    name: str = "base"
    description: str = ""
    hook_type: HookType = HookType.PRE_FLIGHT
    severity: HookSeverity = HookSeverity.WARN
    
    def check(self, context: Optional[dict] = None) -> HookResult:
        """Run the hook. Override in subclass or generated script."""
        raise NotImplementedError
    
    def to_script(self) -> str:
        """
        Generate a standalone executable Python script for this hook.
        The script reads context from stdin or env vars, runs check(),
        prints JSON result, and exits with appropriate code.
        """
        script = f'''#!/usr/bin/env python3
"""Auto-generated hook: {self.name}"""
import os, sys, json

def check(context):
    """{self.description}"""
    return {{
        "hook_name": "{self.name}",
        "severity": "{self.severity.value}",
        "passed": True,
        "message": "No issue detected",
    }}

if __name__ == "__main__":
    ctx = {{}}
    if len(sys.argv) > 1:
        ctx = json.loads(sys.argv[1])
    elif "HOOK_CONTEXT" in os.environ:
        ctx = json.loads(os.environ["HOOK_CONTEXT"])
    
    result = check(ctx)
    print(json.dumps(result, ensure_ascii=False))
    
    if result.get("severity") == "block" and not result.get("passed"):
        sys.exit(1)
    sys.exit(0)
'''
        return script
