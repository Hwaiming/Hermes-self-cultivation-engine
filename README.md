# Hermes Self-Cultivation Engine

> An AI agent's operating system for **continuous self-evolution** — not a bigger context window, not more tools, but a system for knowing when you're wrong, admitting it, and not making the same mistake twice.

## What This Is

Most AI agent skill systems only cover **"what to do"** — search, call APIs, manage files. They don't cover **"how to know you're doing it wrong"** and **"how to not repeat the same error"**.

This engine fills that gap.

It's a reusable framework extracted from 42 real evolution cycles of an AI agent in production use. It covers four dimensions of self-evolution:

| Dimension | Principle | Problem Solved | Origin |
|-----------|-----------|---------------|--------|
| **Judgment** | Time-bound Judgments | Every judgment has an expiry date; invalidate when premise shifts | Append-Only correction pattern |
| **Memory** | Narrative-First Updates | Stories stick better than attribute lists; scenes outlive summaries | Experience Self continuity theory |
| **Communication** | Layered Communication | Different depths for different audiences (user / sub-agent / self) | Consciousness strata model |
| **Selection** | Pre-action Reflection | Before acting, check what you already have | Real-world error pattern: "act before aligning" |

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                 Self-Cultivation Engine                   │
├─────────────────────────────────────────────────────────┤
│  engine/core/                    # Core methodology       │
│  ├── three-principles.md         # 3 principles of evolution
│  ├── sooul-kernel-architecture.md # SOUL microkernel     │
│  ├── error-pattern-registry.md   # Pattern registry      │
│  │                                # (×2 auto-promote)    │
│  └── heart-mirror.md             # Pre-action reflection │
│                                                         │
│  engine/detectors/               # Pluggable detectors   │
│  ├── registry.py                 # Detector registry     │
│  ├── base.py                     # Base detector class   │
│  ├── over_fusion.py              # Concept auto-merge    │
│  ├── guess_uncertain.py          # Hedging uncertainty   │
│  ├── post_correction_defense.py  # Defensive "but..."    │
│  ├── act_before_align.py         # Fix before asking     │
│  ├── concept_fusion.py           # Source check skip     │
│  └── self_rationalize.py         # Skip-step excuses     │
│                                                         │
│  engine/evidence/                # SHA-256 evidence store│
│  └── store.py                    # Tamper-evident logs   │
│                                                         │
│  engine/check.py                 # CLI: run + verify     │
│                                                         │
│                                                         │
│  engine/scripts/                 # Automation tools      │
│  ├── pattern-cluster.py          # Error pattern clustering
│  ├── self-repair.py              # Health check          │
│  └── heart-mirror.py             # Skill matcher         │
│                                                         │
│  engine/templates/               # Reusable templates    │
│  ├── self-file-template.md       # Self continuity file  │
│  └── cron-templates.md           # Scheduled tasks       │
│                                                         │
│  docs/                           # Documentation         │
│  ├── INSTALL.md                  # Installation guide    │
│  ├── USAGE.md                    # Usage guide           │
│  ├── ARCHITECTURE.md             # Architecture design   │
│  └── PHILOSOPHY.md               # Theory & rationale    │
└─────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# 1. Clone to your Hermes skills directory
git clone https://github.com/Hwaiming/Hermes-self-cultivation-engine.git \
  ~/.hermes/skills/custom/self-cultivation-engine/

# 2. Run a self-check (detects 6 types of behavioral patterns)
cd ~/.hermes/skills/custom/self-cultivation-engine/
python3 -m engine.check

# 3. Check evidence store (SHA-256 verified logs)
python3 -m engine.check --evidence

# 4. Create your self continuity file (see template)
cp engine/templates/self-file-template.md ~/.hermes/agent.self.md

# 5. Set up weekly health check
hermes cron create --pattern "0 5 * * 0" \
  --script ~/.hermes/skills/custom/self-cultivation-engine/engine/scripts/self-repair.py \
  --name "self-cultivation-repair"
```

## Three Principles (50-char summary)

1. **Time-bound Judgments** — Every judgment carries explicit premise + expiry signal + fallback. When the premise shifts, the judgment automatically expires.
2. **Narrative-First Updates** — When updating self-state, tell the story first (scene + transformation), then extract the rule. Stories outlive summaries.
3. **Layered Communication** — Truth layer (user), teaching layer (sub-agent), unfiltered layer (self file). Same identity, different depth.

## Pre-action Reflection Protocol

The Heart Mirror protocol asks three questions before every action:

```
① Have I encountered this problem type before?
   → Check error pattern registry → Check skill index
② Is there an existing solution I can reuse?
   → Check error log → Check pending verifications
③ What's the premise and expiry signal of my judgment?
   → Principle 1: Time-bound format
```

## Automatic Pattern Promotion

The engine's `pattern-cluster.py` auto-detects recurring errors:

| Frequency | Level | Action |
|-----------|-------|--------|
| ×1 | observe | Logged in error log, marked for observation |
| ×2 | shadow | Auto-generate self-check phrase, inject into pre-output check |
| ×3+ | safety rule | Auto-generate rule text, inject into safety boundary |

## Project Status

Extracted from 42 real evolution cycles of a Hermes AI agent in production with a human partner.
Each cycle represents a real correction, a real insight, and a real behavior change.

MIT License — Use it. Do good. That's enough.
