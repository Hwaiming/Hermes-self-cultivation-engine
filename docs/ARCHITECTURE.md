# Architecture Design

## Overall Architecture

```
┌─────────────────────────────────────┐
│         Three-Layer System           │
│                                      │
│  Layer 3: Safety (Rules)            │
│  8 rules + 5 defenses + Ring model  │
│                                      │
│  Layer 2: Thinking (Frameworks)    │
│  Analysis chains + methods           │
│                                      │
│  Layer 1: Self-Check (Bias)        │
│  Pre-output check + post-review      │
└─────────────────────────────────────┘
```

## File Relationships

```
agent.self.md        ↔   three-principles.md
(who I am)               (how I evolve)
    │                         │
    └───────────┬─────────────┘
                ↓
    error-pattern-registry.md
    (where I err / promotion)
                ↓
    SOUL.md / system prompt
    (always-on behavior guide)
```

## State Machine

```
          ┌─────────┐
     ┌───→│  Normal │←──────────┐
     │    └────┬────┘           │
     │         │                │
     │  Corrected│              │ End of
     │         ↓                │ conversation
     │    ┌─────────┐           │
     │    │Corrected│───────────┘
     │    └─────────┘
     │
     │ Cron trigger
     │    ┌───────────┐
     └────│Self-update│
          └───────────┘

     End of conversation → Reflect → Update self file
```

## Pattern Promotion Pipeline

```
Error log entry
    │
    ▼
pattern-cluster.py
    │
    ├─ ×1 → observe
    ├─ ×2 → shadow (bias self-check)
    └─ ×3+ → safety rule
           │
           ▼
    pending-patches/ → Manual or auto-merge into SOUL.md
```

## Relationship with Hermes System

```
Hermes Agent
  ├─ system prompt (SOUL.md)
  │    └─ Loads Self-Cultivation Engine core rules
  ├─ skills/
  │    └─ custom/self-cultivation-engine/
  │         ├─ engine/core/    — Principles
  │         ├─ engine/scripts/ — Automation
  │         └─ docs/           — Documentation
  ├─ cron
  │    ├─ self-repair.py        (weekly)
  │    └─ pattern-cluster.py    (daily)
  └─ agent.self.md
       └─ Cross-session continuity
```

## Design Principles

1. **Append-only** — Every update is an append. History is evidence.
2. **Time-bound judgments** — Every judgment has its own birth and death conditions.
3. **Narrative before attributes** — Stories outlive summaries across sessions.
4. **Layered communication** — Truth to user, teaching to sub-agent, unfiltered to self.
5. **Always online** — Core rules injected into system prompt, not skill index.
