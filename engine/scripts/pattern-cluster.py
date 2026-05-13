#!/usr/bin/env python3
"""
Hermes Self-Cultivation Engine · Pattern Cluster
pattern-cluster.py

Reads self file error log → semantic clustering (via LLM API) → 
updates patterns-registry.md → auto-promotion at ×2/×3+ (shadow/iron layers)

Usage:
  python3 pattern-cluster.py              # Full scan + cluster + promote + report
  python3 pattern-cluster.py --dry-run    # Report only, no writes
  python3 pattern-cluster.py --quiet      # JSON output

Config:
  Set SELF_CULTIVATION_HOME env var to the engine root directory.
  Defaults to ~/.hermes/self-cultivation/
  
Requires:
  - DeepSeek API key (in .env or config.yaml)
  - patterns-registry.md in the engine root
  - SOUL.md in the engine root (for shadow/iron layer injection)
"""

import re
import os
import sys
import json
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

# === Paths ===

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
REGISTRY_FILE = ENGINE_HOME / "error-pattern-registry.md"
PENDING_DIR = ENGINE_HOME / "pending-patches"
ENV_FILE = ENGINE_HOME.parent / ".env"
CONFIG_FILE = ENGINE_HOME.parent / "config.yaml"

# === API Config ===

def load_api_key():
    """Three-level fallback: .env → config.yaml → env var"""
    # 1. .env file
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if "DEEPSEEK_API_KEY" in line:
                key = line.split("=", 1)[1].strip().strip("\"'")
                if key.startswith("sk-"):
                    return key
    # 2. config.yaml
    if CONFIG_FILE.exists():
        text = CONFIG_FILE.read_text(encoding="utf-8")
        m = re.search(r"DEEPSEEK_API_KEY\s*[:=]\s*['\"]?(sk-[^'\"\s]+)", text)
        if m:
            return m.group(1)
    # 3. env var
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if key.startswith("sk-"):
        return key
    return None

DEEPSEEK_API_KEY = load_api_key()
DEEPSEEK_ENDPOINT = "https://api.deepseek.com/v1/chat/completions"

# === Pattern Registry ===

PATTERN_PATTERN = re.compile(
    r"### pattern-(\d{3}): (.+?)\n"
    r"- \*\*根因\*\*: (.+?)\n"
    r"- \*\*Frequency\*\*: (\d+)\n"
    r"- \*\*hitCount\*\*: (\d+)\n"
)

def parse_patterns(text):
    """Parse patterns-registry.md into structured data."""
    patterns = {}
    for m in PATTERN_PATTERN.finditer(text):
        pid, name, root_cause, freq, level = m.groups()
        patterns[f"pattern-{pid}"] = {
            "name": name.strip(),
            "root_cause": root_cause.strip(),
            "freq": int(freq),
            "level": level.strip(),
        }
    return patterns

def update_registry(patterns, dry_run=False, quiet=False):
    """Rebuild patterns-registry.md from pattern data."""
    lines = [
        "# 模式家族登记册（Patterns Registry）\n",
        f"> auto-generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n",
        "> frequency ×2 → shadow, ×3+ → iron\n",
        "\n",
    ]
    for pid, p in sorted(patterns.items()):
        lines.extend([
            f"### {pid}: {p['name']}\n",
            f"- **根因**: {p['root_cause']}\n",
            f"- **频次**: {p['freq']}\n",
            f"- **当前层级**: {p['level']}\n",
        ])
        if p.get("entries"):
            lines.append("- **条目**:\n")
            for entry in p["entries"]:
                lines.append(f"  - {entry}\n")
        lines.append("\n")
    
    if dry_run:
        if not quiet:
            print("=== DRY RUN: would write ===")
            print("".join(lines[-10:]))
        return
    
    REGISTRY_FILE.write_text("".join(lines), encoding="utf-8")
    if not quiet:
        print(f"✅ patterns-registry.md updated ({len(patterns)} patterns)")

def promote(pattern, dry_run=False, quiet=False):
    """
    Promote pattern if frequency crosses threshold.
    ×2 → inject shadow self-check into pending-patches/
    ×3+ → inject iron rule into pending-patches/
    """
    freq = pattern["freq"]
    level = pattern["level"]
    name = pattern["name"]
    
    target_level = None
    if freq >= 3 and level != "iron":
        target_level = "iron"
    elif freq >= 2 and level == "practice":
        target_level = "shadow"
    
    if not target_level:
        return None
    
    if target_level == "shadow":
        content = f"""* **{name}**（模式触发频次×{freq}，已自动晋升）→ 扫描：当前是否正在激活此偏差？"""
    else:  # iron
        content = f"""### 铁律N：{name}
根因：{pattern['root_cause']}。此模式已出现 {freq} 次，已超过铁律升级阈值。
**触发条件：**
1. {pattern.get('trigger', '场景接近上述条目描述时')}
**标准动作：**
{pattern.get('action', '先确认再执行，不得自行决定。')}
"""
    
    if dry_run:
        if not quiet:
            print(f"  [DRY RUN] Would promote #{name} → {target_level}")
        return f"would_promote_{name}_{target_level}"
    
    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fff_-]', '_', name)
    patch_file = PENDING_DIR / f"{timestamp}_{safe_name}_{target_level}.md"
    patch_file.write_text(content, encoding="utf-8")
    
    if not quiet:
        print(f"  ⬆ Promoted #{name}: practice→{target_level} (×{freq})")
        print(f"     Patch: {patch_file}")
    
    return f"{name}_{target_level}"

# === Session Search ===

def get_recent_sessions(days=7):
    """Get recent session errors via hermes CLI."""
    try:
        result = subprocess.run(
            ["hermes", "sessions", "list", "--days", str(days)],
            capture_output=True, text=True, timeout=30
        )
        return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""

# === Report ===

def report(patterns, promotions, dry_run=False, quiet=False):
    """Print summary report."""
    if quiet:
        print(json.dumps({
            "patterns": {k: {"freq": v["freq"], "level": v["level"]} for k, v in patterns.items()},
            "promotions": promotions,
            "dry_run": dry_run,
        }, ensure_ascii=False))
        return
    
    print(f"\n{'='*60}")
    print(f"  模式聚类晋升报告")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    if dry_run:
        print(f"  [DRY RUN — no files written]")
    print(f"{'='*60}")
    
    for pid, p in sorted(patterns.items()):
        icon = {"practice": "○", "shadow": "◐", "iron": "●"}.get(p["level"], "○")
        print(f"  {icon} {pid}: {p['name']} (×{p['freq']}, {p['level']})")
    
    print(f"\n  晋升: {len(promotions)}")
    for prom in promotions:
        print(f"    ⬆ {prom}")
    print(f"{'='*60}\n")

# === Main ===

def main():
    parser = argparse.ArgumentParser(description="Pattern cluster and promotion engine")
    parser.add_argument("--dry-run", action="store_true", help="Report only, no writes")
    parser.add_argument("--quiet", action="store_true", help="JSON output")
    args = parser.parse_args()
    
    if not DEEPSEEK_API_KEY:
        print("⚠️  No DeepSeek API key found. Skipping semantic clustering.")
        # Fall back to local analysis only
        patterns = parse_patterns(REGISTRY_FILE.read_text(encoding="utf-8") if REGISTRY_FILE.exists() else "")
        report(patterns, [], dry_run=args.dry_run, quiet=args.quiet)
        return 0
    
    # Parse existing registry
    existing_text = REGISTRY_FILE.read_text(encoding="utf-8") if REGISTRY_FILE.exists() else ""
    patterns = parse_patterns(existing_text)
    
    if not patterns:
        print("📝 No patterns found in registry. Run a few sessions first.")
        return 0
    
    # Check for promotions
    promotions = []
    for pid, p in sorted(patterns.items()):
        result = promote(p, dry_run=args.dry_run, quiet=args.quiet)
        if result:
            promotions.append(result)
    
    report(patterns, promotions, dry_run=args.dry_run, quiet=args.quiet)
    return 0

if __name__ == "__main__":
    sys.exit(main())
