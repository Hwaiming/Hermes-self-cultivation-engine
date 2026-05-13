#!/usr/bin/env python3
"""
问心镜 v2 — Hermes Skill 自动匹配器
Heart Mirror: Skill matching engine for self-cultivation.

Before acting, check what skills/tools you already have.
Prevents reinventing wheels and concept confusion.

Usage:
  python3 heart-mirror.py "我想存一份项目文档"
  python3 heart-mirror.py "帮我排查这个 bug" --top 5
  python3 heart-mirror.py "研究一下新的开源工具" --format json

Config:
  Set SKILLS_DIR env var to scan a custom skills directory.
  Default: ~/.hermes/skills/
"""

import os
import re
import sys
import json
import argparse
from pathlib import Path

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

# ─── Config ─────────────────────────────────────────

DEFAULT_SKILLS_DIR = os.path.expanduser(os.environ.get(
    "SKILLS_DIR", "~/.hermes/skills"
))
DEFAULT_TOP_N = 3

WEIGHTS = {
    "name_exact": 5,
    "name_partial": 3,
    "trigger": 4,
    "tag": 3,
    "description": 2,
    "related": 1,
    "category": 1,
    "intent": 3,
}

# ─── Tokenizer ──────────────────────────────────────

def tokenize(text: str) -> set:
    """Split text into lowercase token set."""
    if not text:
        return set()
    text = text.lower()
    tokens = set()
    for word in re.findall(r'[a-z][a-z0-9\-]+', text):
        tokens.add(word)
    chinese_chars = re.findall(r'[\u4e00-\u9fff]+', text)
    for phrase in chinese_chars:
        tokens.add(phrase)
        for i in range(len(phrase) - 1):
            tokens.add(phrase[i:i+2])
    return tokens

STOPWORDS = {
    '我', '的', '了', '是', '在', '有', '和', '就', '不', '人', '都', '一',
    '一个', '这个', '那个', '怎么', '什么', '如何', '可以', '需要', '想要',
    'the', 'is', 'it', 'to', 'of', 'in', 'for', 'on', 'with', 'at',
    'by', 'that', 'this', 'are', 'was', 'were', 'have', 'has', 'had',
    'do', 'does', 'did', 'but', 'not', 'or', 'if', 'as',
}

def extract_keywords(text: str) -> set:
    tokens = tokenize(text)
    return {t for t in tokens if t not in STOPWORDS}

# ─── SKILL.md Parser ────────────────────────────────

def parse_skill_md(text: str) -> dict:
    """Parse SKILL.md frontmatter into metadata dict."""
    meta = {
        "name": "", "description": "", "triggers": [],
        "tags": [], "category": "", "related_skills": [],
        "intent": "",
    }
    
    # Try YAML first
    if HAS_YAML:
        m = re.search(r'^---\s*\n(.*?)\n---', text, re.DOTALL)
        if m:
            try:
                parsed = yaml.safe_load(m.group(1))
                if isinstance(parsed, dict):
                    h = parsed.get("hermes", parsed)
                    meta["name"] = str(parsed.get("name", ""))
                    meta["description"] = str(parsed.get("description", ""))
                    meta["category"] = str(h.get("category", ""))
                    meta["tags"] = h.get("tags", [])
                    meta["triggers"] = h.get("triggers", [])
                    meta["related_skills"] = h.get("related_skills", [])
                    meta["intent"] = str(parsed.get("intent", ""))
                    return meta
            except (yaml.YAMLError, AttributeError):
                pass
    
    # Fallback: manual regex parsing
    lines = text.split('\n')
    in_frontmatter = False
    pipe_mode = False
    pipe_key = None
    current_list_key = None
    current_list = []
    
    for line in lines:
        stripped = line.strip()
        
        if stripped == '---':
            in_frontmatter = not in_frontmatter
            continue
        if not in_frontmatter:
            break
        
        if pipe_mode:
            if stripped:
                meta[pipe_key] = (meta.get(pipe_key, '') + ' ' + stripped).strip()
                continue
            else:
                pipe_mode = False
                pipe_key = None
        
        kv_match = re.match(r'^(\w[\w\-]*):\s*(.*)', stripped)
        if kv_match:
            key = kv_match.group(1)
            value = kv_match.group(2).strip()
            
            if key in ('description',):
                if value in ('|', '>', '>-', '|-'):
                    pipe_mode = True
                    pipe_key = key
                    meta[key] = ''
                else:
                    meta[key] = value.lstrip('> ').strip("'\"")
            elif key in ('name', 'category'):
                meta[key] = value.strip("'\"")
            elif key in ('triggers', 'tags', 'related_skills'):
                if value.startswith('['):
                    items = re.findall(r"'([^']*)'|\"([^\"]*)\"|([^,\[\]\s]+)", value)
                    meta[key] = [i[0] or i[1] or i[2] for i in items if (i[0] or i[1] or i[2])]
                elif value:
                    meta[key] = [value.strip("'\"")]
                else:
                    current_list_key = key
                    current_list = []
            
            # Handle nested metadata.hermes.*
            nested = re.match(r'metadata\.hermes\.(\w+)', key)
            if nested and value:
                sub_key = nested.group(1)
                if sub_key in ('triggers', 'tags', 'related_skills'):
                    if value.startswith('['):
                        items = re.findall(r"'([^']*)'|\"([^\"]*)\"|([^,\[\]\s]+)", value)
                        meta[sub_key] = [i[0] or i[1] or i[2] for i in items if (i[0] or i[1] or i[2])]
                    else:
                        meta[sub_key] = [value.strip("'\"")]
    
    return meta


def scan_skills(skills_dir: str) -> list:
    """Scan all SKILL.md files, return metadata list."""
    skills = []
    base = Path(skills_dir)
    
    if not base.exists():
        return skills
    
    for skill_file in sorted(base.glob("**/SKILL.md")):
        try:
            text = skill_file.read_text(encoding='utf-8', errors='replace')
        except Exception:
            continue
        
        meta = parse_skill_md(text)
        meta["_path"] = str(skill_file)
        
        # Derive name from path if not in frontmatter
        if not meta["name"]:
            meta["name"] = skill_file.parent.name
        
        skills.append(meta)
    
    return skills


def match(query: str, skills: list, top_n: int = 3) -> list:
    """
    Match query against skills, return ranked results.
    Uses weighted scoring across name/triggers/description/tags.
    """
    keywords = extract_keywords(query)
    if not keywords:
        return []
    
    scored = []
    for skill in skills:
        score = 0.0
        
        name_words = tokenize(skill.get("name", ""))
        desc_words = tokenize(skill.get("description", ""))
        trigger_words = set()
        for t in skill.get("triggers", []):
            trigger_words |= tokenize(t)
        tag_words = set()
        for t in skill.get("tags", []):
            tag_words |= tokenize(t)
        intent_words = tokenize(skill.get("intent", ""))
        
        overlap = keywords & name_words
        if len(overlap) == len(keywords) == len(name_words) and len(name_words) > 0:
            score += WEIGHTS["name_exact"]
        elif overlap:
            score += WEIGHTS["name_partial"] * (len(overlap) / max(len(keywords), 1))
        
        # Triggers match
        trigger_overlap = keywords & trigger_words
        if trigger_overlap:
            score += WEIGHTS["trigger"] * (len(trigger_overlap) / max(len(trigger_words), 1))
        
        # Description match
        desc_overlap = keywords & desc_words
        if desc_overlap:
            score += WEIGHTS["description"] * (len(desc_overlap) / max(len(desc_words), 1))
        
        # Tags match
        tag_overlap = keywords & tag_words
        if tag_overlap:
            score += WEIGHTS["tag"] * (len(tag_overlap) / max(len(tag_words), 1))
        
        # Intent match
        intent_overlap = keywords & intent_words
        if intent_overlap:
            score += WEIGHTS["intent"] * (len(intent_overlap) / max(len(intent_words), 1))
        
        if score > 0:
            scored.append((score, skill))
    
    scored.sort(key=lambda x: -x[0])
    return scored[:top_n]


def format_result(results: list, fmt: str = "text") -> str:
    """Format match results."""
    if fmt == "json":
        data = []
        for score, skill in results:
            data.append({
                "name": skill.get("name", ""),
                "score": round(score, 1),
                "description": skill.get("description", ""),
                "path": skill.get("_path", ""),
            })
        return json.dumps(data, ensure_ascii=False, indent=2)
    
    lines = []
    for i, (score, skill) in enumerate(results, 1):
        name = skill.get("name", "?")
        desc = skill.get("description", "")
        trigger_hint = ""
        if skill.get("triggers"):
            trigger_hint = f"  触发器: {', '.join(skill['triggers'][:3])}"
        lines.append(f"{i}. {name} ({score:.0f}%)")
        if desc:
            lines.append(f"   → {desc}")
        if trigger_hint:
            lines.append(trigger_hint)
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="问心镜 — Skill auto-matcher")
    parser.add_argument("query", nargs="?", help="Task description to match against")
    parser.add_argument("--top", type=int, default=DEFAULT_TOP_N, help=f"Top N results (default: {DEFAULT_TOP_N})")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    parser.add_argument("--refresh", action="store_true", help="Force rescan")
    parser.add_argument("--stats", action="store_true", help="Show skill count statistics")
    args = parser.parse_args()
    
    skills = scan_skills(DEFAULT_SKILLS_DIR)
    
    if args.stats:
        print(f"问心镜: {len(skills)} skills scanned from {DEFAULT_SKILLS_DIR}")
        categories = {}
        for s in skills:
            cat = s.get("category", "uncategorized")
            categories[cat] = categories.get(cat, 0) + 1
        for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
            print(f"  {cat}: {count}")
        return 0
    
    if not args.query:
        print("问心镜: 问什么？用 --query 或直接传参数")
        parser.print_help()
        return 1
    
    results = match(args.query, skills, top_n=args.top)
    
    if not results:
        print(f"问心镜: 未找到匹配 '{args.query}' 的技能")
        return 0
    
    print(format_result(results, fmt=args.format))
    return 0


if __name__ == "__main__":
    sys.exit(main())
