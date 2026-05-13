#!/usr/bin/env python3
"""Auto-generated hook: act_before_align
Severity: block
Source: pattern: act_before_align
Generated: 2026-05-13 09:44

This hook checks for: Default reaction to "found a problem" is "let me fix it" instead of "let me align first." Decision space not fully scanned before acting.
"""

import os
import sys
import json


def check(context: dict) -> dict:
    """Check for: Default reaction to "found a problem" is "let me fix it" instead of "let me align first." Decision space not fully scanned before acting."""
    
    output = context.get("output", "")
    found_problem = context.get("found_problem", False)
    has_options = context.get("has_multiple_options", False)
    
    if not found_problem or not output:
        return {"hook_name": "act_before_align", "severity": "block", "passed": True, "message": "No problem context"}
    
    fix_phrases = [p.lower() for p in [
        "let me fix", "let me correct", "i'll fix", "i'll correct",
        "i'll update", "let me update", "i'll change", "i'll rebuild",
    ]]
    align_phrases = [p.lower() for p in [
        "let me check", "let me verify", "should i", "shall i",
        "do you want", "let me ask", "let me confirm",
    ]]
    
    ol = output.lower()
    fix_count = sum(1 for p in fix_phrases if p in ol)
    align_count = sum(1 for p in align_phrases if p in ol)
    
    if has_options and fix_count > 0 and fix_count >= align_count:
        return {
            "hook_name": "act_before_align", "severity": "block",
            "passed": False,
            "message": f"Acted before aligning (fix:{fix_count}, align:{align_count})",
        }
    
    if fix_count > 0 and align_count == 0:
        return {
            "hook_name": "act_before_align", "severity": "block",
            "passed": False,
            "message": "Direct fix without alignment check",
        }
    
    return {"hook_name": "act_before_align", "severity": "block", "passed": True, "message": "No issue"}

    return {
        "hook_name": "act_before_align",
        "severity": "block",
        "passed": True,
        "message": "No issue detected",
    }


if __name__ == "__main__":
    ctx = {}
    if len(sys.argv) > 1:
        ctx = json.loads(sys.argv[1])
    elif "HOOK_CONTEXT" in os.environ:
        ctx = json.loads(os.environ["HOOK_CONTEXT"])
    
    result = check(ctx)
    result["generated_at"] = "2026-05-13 09:44"
    print(json.dumps(result, ensure_ascii=False))
    
    if result.get("severity") == "block" and not result.get("passed"):
        sys.exit(1)
    sys.exit(0)
