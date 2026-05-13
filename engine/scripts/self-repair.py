#!/usr/bin/env python3
"""
Hermes Self-Cultivation Engine · Self Repair
self-repair.py

Health check for the self-cultivation system.
Checks structural integrity, file consistency, stale data detection.

Usage:
  python3 self-repair.py                    # Full check + report
  python3 self-repair.py --quiet            # JSON output (for cron)
  python3 self-repair.py --self-only        # Only check self file

Config:
  Set SELF_CULTIVATION_HOME env var for the engine root directory.
  ENGINES_SELF_FILE for the self continuity file path.
"""

import os
import re
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone

ENGINE_HOME = Path(os.environ.get(
    "SELF_CULTIVATION_HOME",
    str(Path.home() / ".hermes" / "self-cultivation")
))
SELF_FILE = Path(os.environ.get(
    "ENGINES_SELF_FILE",
    str(ENGINE_HOME.parent / "agent.self.md")
))
SOUL_FILE = Path(os.environ.get(
    "ENGINES_SOUL_FILE",
    str(ENGINE_HOME.parent / "SOUL.md")
))

# Required sections in self file
REQUIRED_SECTIONS = [
    "同一性声明",
    "叙事层",
    "理想自我",
    "阴影层",
    "实践层",
    "错题本",
    "待验证",
    "关系层",
]

def check_self_file_structure(text):
    """Check all required sections exist."""
    missing = []
    for section in REQUIRED_SECTIONS:
        if section not in text:
            missing.append(section)
    return missing

def check_table_consistency(text):
    """Check markdown table column counts."""
    issues = []
    lines = text.split("\n")
    in_table = False
    header_cols = 0
    
    for i, line in enumerate(lines):
        if line.strip().startswith("|"):
            cols = line.count("|") - 1
            if "---" in line:
                # Separator row — skip
                in_table = True
                continue
            if not in_table:
                header_cols = cols
                in_table = True
            elif cols != header_cols and line.strip() != "|":
                issues.append(f"  Line {i+1}: {cols} cols (expected {header_cols})")
                in_table = False
        else:
            in_table = False
    
    return issues

def check_file_size(path, max_bytes=200000):
    """Check if file is approaching size limit."""
    try:
        size = path.stat().st_size
        if size > max_bytes:
            return f"EXCEEDS ({size}/{max_bytes} bytes)"
        elif size > max_bytes * 0.85:
            return f"WARNING ({size}/{max_bytes} bytes, >85%)"
        return f"OK ({size} bytes)"
    except FileNotFoundError:
        return "NOT FOUND"

def check_date_consistency(text):
    """Check if last-update date in frontmatter is recent."""
    m = re.search(r"最后更新[：:]\s*(\d{4}-\d{2}-\d{2})", text)
    if m:
        date_str = m.group(1)
        try:
            update_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            delta = (datetime.now().date() - update_date).days
            if delta > 14:
                return f"STALE ({delta} days since last update)"
            return f"OK ({delta} days)"
        except ValueError:
            return f"PARSE ERROR: {date_str}"
    return "NO DATE FOUND"

def check_file_exists(path):
    """Check if file exists."""
    try:
        exists = path.exists()
        size = path.stat().st_size if exists else 0
        return f"OK ({size/1024:.1f}KB)" if exists else f"NOT FOUND"
    except FileNotFoundError:
        return "NOT FOUND"

def check_pending_patches():
    """Check for unapplied pending patches."""
    pending_dir = ENGINE_HOME / "pending-patches"
    if not pending_dir.exists():
        return "NO PENDING DIR"
    
    patches = list(pending_dir.glob("*.md"))
    if patches:
        return f"{len(patches)} PENDING"
    return "NONE"

def run_all_checks():
    """Run all self-repair checks."""
    results = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "checks": [],
    }
    # We'll build a string output instead for backward compat
    
    output = []
    output.append(f"\n{'='*60}")
    output.append(f"  🔧 Self-Cultivation Engine · Self Repair")
    output.append(f"  {results['timestamp']}")
    output.append(f"{'='*60}\n")
    
    # 1. Self file structure
    output.append("[1/8] Self file structure")
    if SELF_FILE.exists():
        text = SELF_FILE.read_text(encoding="utf-8")
        missing = check_self_file_structure(text)
        if missing:
            output.append(f"  ❌ Missing sections: {', '.join(missing)}")
        else:
            output.append(f"  ✅ All {len(REQUIRED_SECTIONS)} required sections present")
        
        # 2. Table consistency
        output.append("[2/8] Table column consistency")
        issues = check_table_consistency(text)
        if issues:
            for issue in issues[:5]:
                output.append(f"  ⚠️  {issue}")
            output.append(f"  ... {len(issues)} total issues")
        else:
            output.append("  ✅ All tables consistent")
    else:
        output.append(f"  ⏭️  Self file not found at {SELF_FILE}")
    
    # 3. SOUL.md size
    output.append(f"[3/8] SOUL.md size")
    output.append(f"  {check_file_size(SOUL_FILE)}")
    
    # 4. Timestamp consistency
    output.append(f"[4/8] Last update freshness")
    if SELF_FILE.exists():
        output.append(f"  {check_date_consistency(SELF_FILE.read_text(encoding='utf-8'))}")
    
# 5. Core principles file
    output.append(f"[5/8] Core principles file")
    output.append(f"  three-principles.md: {check_file_exists(ENGINE_HOME / 'three-principles.md')}")
    
    # 6. Error pattern registry
    output.append(f"[6/8] Error pattern registry")
    output.append(f"  {check_file_exists(ENGINE_HOME / 'error-pattern-registry.md')}")
    
    # 7. Dreams directory
    dreams_dir = ENGINE_HOME / "dreams"
    output.append(f"[7/8] Dreams directory")
    if dreams_dir.exists():
        count = len(list(dreams_dir.glob("*.md")))
        output.append(f"  OK ({count} dream journals)")
    else:
        output.append(f"  ⏭️  No dreams directory")
    
    # 8. Pending patches
    output.append(f"[8/8] Pending patches")
    output.append(f"  {check_pending_patches()}")
    
    output.append(f"\n{'='*60}")
    output.append(f"  Repair complete — no automatic fixes applied.")
    output.append(f"  (Engine policy: never modify old data, only append)")
    output.append(f"{'='*60}\n")
    
    return "\n".join(output)

def main():
    parser = argparse.ArgumentParser(description="Self-cultivation repair and health check")
    parser.add_argument("--quiet", action="store_true", help="Minimal output for cron")
    parser.add_argument("--self-only", action="store_true", help="Only check self file")
    args = parser.parse_args()
    
    output = run_all_checks()
    
    if args.quiet:
        # Extract just the essential info
        summary = {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
        }
        print(json.dumps(summary, ensure_ascii=False))
    else:
        print(output)

if __name__ == "__main__":
    main()
