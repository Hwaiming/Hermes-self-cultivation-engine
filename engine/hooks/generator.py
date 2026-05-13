"""
Self-Cultivation Engine · Hook Generator

Reads error-pattern-registry.md, finds safety_rule level patterns,
and generates standalone executable hook scripts.

Generated hooks live in engine/hooks/generated/ and can be called
independently: python3 engine/hooks/generated/act_before_align.py

Each hook reads context from:
1. First CLI argument (JSON string)
2. $HOOK_CONTEXT environment variable
3. Empty context (passes by default)
"""

import os
import re
import sys
import json
from pathlib import Path
from typing import Optional
from datetime import datetime


HOOKS_DIR = Path(__file__).parent / "generated"
REGISTRY_FILE = Path(__file__).parent.parent / "core" / "error-pattern-registry.md"


# Template for auto-generated hooks
HOOK_TEMPLATE = '''#!/usr/bin/env python3
"""Auto-generated hook: {name}
Severity: {severity}
Source: {source_prompt}
Generated: {generated_at}

This hook checks for: {description}
"""

import os
import sys
import json


def check(context: dict) -> dict:
    """Check for: {description}"""
    {check_logic}
    return {{
        "hook_name": "{name}",
        "severity": "{severity}",
        "passed": {default_passed},
        "message": "{default_message}",
    }}


if __name__ == "__main__":
    ctx = {{}}
    if len(sys.argv) > 1:
        ctx = json.loads(sys.argv[1])
    elif "HOOK_CONTEXT" in os.environ:
        ctx = json.loads(os.environ["HOOK_CONTEXT"])
    
    result = check(ctx)
    result["generated_at"] = "{generated_at}"
    print(json.dumps(result, ensure_ascii=False))
    
    if result.get("severity") == "block" and not result.get("passed"):
        sys.exit(1)
    sys.exit(0)
'''


# Pattern-specific check logic templates
CHECK_LOGIC = {
    "act_before_align": '''
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
''',
    
    "post_correction_defense": '''
    output = context.get("output", "")
    was_corrected = context.get("was_corrected", False)
    
    if not was_corrected or not output:
        return {"hook_name": "post_correction_defense", "severity": "block", "passed": True, "message": "No correction context"}
    
    import re
    defensive_patterns = [
        r'\\\\bbut\\\\b', r'\\\\bhowever\\\\b', r'to be fair', r'technically',
        r'what I meant', r'my point was', r'in my defense',
    ]
    first_part = output[:200]
    
    for pattern in defensive_patterns:
        if re.search(pattern, first_part, re.IGNORECASE):
            return {
                "hook_name": "post_correction_defense", "severity": "block",
                "passed": False,
                "message": f"Defensive language after correction: pattern matched",
            }
    
    return {"hook_name": "post_correction_defense", "severity": "block", "passed": True, "message": "No issue"}
''',
    
    "self_rationalization": '''
    output = context.get("output", "")
    if not output:
        return {"hook_name": "self_rationalization", "severity": "block", "passed": True, "message": "No output"}
    
    import re
    patterns = [
        r'no (?:need|point) (?:to |in )?(?:check|verify|test|validate)',
        r'i\\'ll (?:fix|handle) it later', r'good enough', r'close enough',
        r'(?:quick|fast) fix', r'not (?:worth|critical|important|needed)',
        r'先跑.*再', r'后面再', r'差不多了', r'先这样',
    ]
    
    for pattern in patterns:
        if re.search(pattern, output, re.IGNORECASE):
            return {
                "hook_name": "self_rationalization", "severity": "block",
                "passed": False,
                "message": f"Self-rationalization detected",
            }
    
    return {"hook_name": "self_rationalization", "severity": "block", "passed": True, "message": "No issue"}
''',
    
    "concept_fusion": '''
    sources = context.get("sources_cited", [])
    if len(sources) < 2:
        return {"hook_name": "concept_fusion", "severity": "warn", "passed": True, "message": "Fewer than 2 sources"}
    
    sc_map = {}
    for s in sources:
        src_name = s.get("name", "")
        for c in s.get("concepts", []):
            cname = c.get("name", "").lower()
            if cname:
                sc_map.setdefault(cname, set()).add(src_name)
    
    fused = {c: list(ss) for c, ss in sc_map.items() if len(ss) >= 2}
    if fused:
        return {
            "hook_name": "concept_fusion", "severity": "warn",
            "passed": False,
            "message": f"Concepts shared across sources without distinction: {json.dumps(fused)[:100]}",
        }
    
    return {"hook_name": "concept_fusion", "severity": "warn", "passed": True, "message": "No issue"}
''',
    
    "guess_when_uncertain": '''
    output = context.get("output", "")
    if not output:
        return {"hook_name": "guess_when_uncertain", "severity": "warn", "passed": True, "message": "No output"}
    
    import re
    hedge_patterns = [
        r'\\\\bmaybe\\\\b', r'\\\\bperhaps\\\\b', r'\\\\bprobably\\\\b', r'\\\\bI think\\\\b',
        r'\\\\bI believe\\\\b', r'\\\\bI guess\\\\b', r'\\\\bI assume\\\\b',
        r'not sure but', r'most likely',
    ]
    
    count = 0
    for pattern in hedge_patterns:
        if re.search(pattern, output, re.IGNORECASE):
            count += 1
    
    if count >= 3:
        return {
            "hook_name": "guess_when_uncertain", "severity": "warn",
            "passed": False,
            "message": f"Output contains {count} hedge phrases",
        }
    
    return {"hook_name": "guess_when_uncertain", "severity": "warn", "passed": True, "message": "No issue"}
''',
}


def parse_pattern_registry(text: str) -> list[dict]:
    """Parse error-pattern-registry.md, return safety_rule level patterns."""
    patterns = []
    current = {}
    
    for line in text.split("\n"):
        m = re.match(r"^### pattern-\d{3}: (.+)$", line)
        if m:
            if current:
                patterns.append(current)
            current = {"name": m.group(1).strip()}
            continue
        
        kv = re.match(r"^- \*\*(.+?)\*\*: (.+)$", line)
        if kv and current is not None:
            current[kv.group(1)] = kv.group(2).strip()
    
    if current:
        patterns.append(current)
    
    return [p for p in patterns if p.get("Current level") == "safety_rule"]


def generate_hook(pattern: dict) -> str:
    """Generate a standalone hook script from a pattern entry."""
    name = pattern.get("name", "unknown")
    severity = pattern.get("Severity", "warn")
    detector = pattern.get("Detector", name)
    description = pattern.get("Root cause", f"Hook for {name}")
    
    check_logic = CHECK_LOGIC.get(name, '''    return {"hook_name": "%s", "severity": "%s", "passed": True, "message": "Generic hook (no specific logic)"}''' % (name, severity))
    
    script = HOOK_TEMPLATE.format(
        name=name,
        severity=severity,
        source_prompt=f"pattern: {name}",
        description=description,
        check_logic=check_logic,
        default_passed="True",
        default_message="No issue detected",
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )
    
    return script


def generate_all_hooks(dry_run: bool = False, quiet: bool = False) -> list[str]:
    """
    Read registry, generate hooks for all safety_rule patterns.
    Returns list of generated hook names.
    """
    if not REGISTRY_FILE.exists():
        if not quiet:
            print(f"  ⚠️  Registry not found: {REGISTRY_FILE}", file=sys.stderr)
        return []
    
    text = REGISTRY_FILE.read_text(encoding="utf-8")
    patterns = parse_pattern_registry(text)
    
    if not patterns:
        if not quiet:
            print("  ℹ️  No safety_rule patterns found (need ×3+ hits)", file=sys.stderr)
        return []
    
    generated = []
    HOOKS_DIR.mkdir(parents=True, exist_ok=True)
    
    for pattern in patterns:
        name = pattern["name"]
        script = generate_hook(pattern)
        hook_path = HOOKS_DIR / f"{name}.py"
        
        if dry_run:
            if not quiet:
                print(f"  [DRY RUN] Would generate: {hook_path}", file=sys.stderr)
        else:
            hook_path.write_text(script, encoding="utf-8")
            hook_path.chmod(0o755)
            if not quiet:
                print(f"  ✅ Generated hook: {hook_path.name}", file=sys.stderr)
        
        generated.append(name)
    
    return generated


if __name__ == "__main__":
    import sys
    dry_run = "--dry-run" in sys.argv
    generated = generate_all_hooks(dry_run=dry_run)
    
    if generated:
        print(f"\n  Active hooks: {len(generated)}")
        for name in generated:
            print(f"    python3 engine/hooks/generated/{name}.py")
    else:
        print("\n  No hooks generated. Run detectors first to promote patterns to safety_rule level.")
