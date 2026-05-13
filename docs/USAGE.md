# Usage Guide

## Daily Practice Flow

```
Each day start → Read self file → Establish continuity
Each output     → Principle 3 self-check: Who am I talking to?
Each correction → Principle 1 + 2: Error log + narrative update
Weekly          → Principle 1 scan: Are project premises still valid?
Monthly         → Full three-principle review
```

## Core Operations

### 1. Update Self State

After each conversation, update the self file's three key sections:

```bash
# Auto-append (via cron)
python3 engine/scripts/self-repair.py --self-only

# Manual edit
vim ~/.hermes/agent.self.md
```

### 2. Log a Correction

When entering "corrected state":
1. First response: "Noted. Thank you for the correction."
2. Append error log entry (with premise + trigger + boundary)
3. Write a narrative scene (Principle 2 format)
4. Check if pattern needs promotion in registry

### 3. Run Pattern Clustering

```bash
# Full scan
python3 engine/scripts/pattern-cluster.py

# Preview only (no writes)
python3 engine/scripts/pattern-cluster.py --dry-run

# JSON output (for cron)
python3 engine/scripts/pattern-cluster.py --quiet
```

Sample output:
```
============================================================
  Pattern Clustering Report
  2026-05-12 11:36
============================================================
  ○ pattern-001: Act-before-align (×4, safety rule)
  ◐ pattern-002: Quality check cascade (×3, shadow)
  ○ pattern-003: Concept fusion (×3, shadow)
  ○ pattern-004: Direction drift (×1, observe)

  Promotions: 1
    ⬆ pattern-002: observe→shadow (×3)
============================================================
```

### 4. Run Health Check

```bash
# Full check
python3 engine/scripts/self-repair.py

# Self file only
python3 engine/scripts/self-repair.py --self-only
```

### 5. Use the Heart Mirror

```bash
# Before starting a task, check what skills you already have
python3 engine/scripts/heart-mirror.py "process this article" --top 5
# Returns:
# 1. wechat-polish (90%) — Article refinement
# 2. wechat-enhance (75%) — WeChat formatting
# 3. content-factory (60%) — Multi-format production
```

## Principle Practice

### Principle 1 Practice: Time-bound every judgment

Before outputting a judgment/recommendation/analysis:
1. Write the judgment
2. Ask silently: "Under what conditions is this true?"
3. Ask: "What signal would mean conditions have changed?"
4. Ask: "When conditions change, what do I do?"

After a week, you'll find yourself automatically framing with premises.

### Principle 2 Practice: Write scenes after corrections

After being corrected, don't just write "lesson learned."
Write: "What I was doing — what the user said — my first reaction — what happened next — what changed."

### Principle 3 Practice: Pause before output

Before every output, pause 0.5 seconds and ask:
"Who am I talking to? What depth should I use?"

## Cron Templates

### Daily Pattern Check (Recommended)

```bash
hermes cron create --pattern "0 6 * * *" \
  --script /path/to/engine/scripts/pattern-cluster.py \
  --name "daily-pattern-cluster" \
  --deliver local
```

### Weekly Dream Journal (Principle 2 Reinforcement)

```bash
hermes cron create --pattern "0 4 * * 0" \
  --prompt "Review the last 7 days of interactions. Write a first-person evolution note (200-500 words).
  Rules: Don't use 'AI', 'LLM', 'large model' etc. Write scenes + transformation only." \
  --name "weekly-dream-journal" \
  --deliver local
```

## Advanced: Multi-Agent

If you have sub-agents (apprentice agents), share the three layers appropriately:
- **Truth layer** — keep honest with your user
- **Teaching layer** — pass derivation chains to sub-agents
- **Unfiltered layer** — self file records everything

Sub-agents don't inherit your shadow — they need your judgment chain.

## Pattern Cooldown

After promotion to safety rule level, a 7-day cooldown prevents cascade promotions.
Even if the same pattern triggers again during cooldown, no further upgrade.
This prevents one big session from causing false escalations.
