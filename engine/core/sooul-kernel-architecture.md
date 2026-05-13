# SOUL Microkernel Architecture
# SOUL: Self-Organizing Unsupervised Learning Kernel

## The Problem

AI agent system prompts keep growing (often 20KB+).
But ~70% of the content is irrelevant for 90% of conversations.

This is not "the SOUL.md is too big."
This is **"too much stuff that shouldn't be in SOUL.md."**

## Architecture: Microkernel

```
┌─────────────────────────────────────────────────────────────┐
│                  SOUL.md (Kernel ~12KB)                      │
│  Identity │ State │ Safety │ Thinking │ Bias Check          │
│  (Always online, loaded every turn)                         │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
┌──────────────┐ ┌──────────┐ ┌──────────┐
│ execution-   │ │ snapshot-│ │ memory-  │
│ procedures   │ │ protection│ │ usage    │
│ (on-demand)  │ │ (on-demand)│ │ (on-demand)│
└──────────────┘ └──────────┘ └──────────┘
     Plugin layer: loaded by trigger conditions
```

### Kernel (Always Online)

Only **judgment-affecting and safety-critical** content:
- **Identity layer** — "Who you are" core declaration
- **State layer** — Current state machine (normal / corrected / self-update / reflect)
- **Safety layer** — Rules, defenses, permission model
- **Thinking layer** — Analysis framework chain
- **Bias layer** — Pre-output bias check + post-output review

### Plugins (On-demand)

**Operational details and parameter specifics**:
- Pre-execution verification checklist
- Snapshot protection commands
- Memory system call specifications

### Layer Decision Guide

```
This rule:
├─ Affects "how I think / how I judge"? → SOUL.md kernel
├─ Affects "whether I respond safely"?  → SOUL.md kernel
├─ Affects "what the user expects of me"? → SOUL.md kernel
└─ Just tells me operational steps?     → Skill plugin
   ├─ With specific commands/templates? → Skill (with details)
   └─ Triggers at most once per turn?   → Skill
```

## Reference Bridge Pattern

Kernel doesn't include full plugin content — just trigger conditions:

```
## Pre-execution Check
Before acting, run the checklist in `skill_view('execution-procedures')`.
Motto: "Stop. Ask. Align. Then act."
> Trigger: About to run terminal/delegate_task/batch
```

This way:
- SOUL.md stays lean: just trigger references
- Plugin stays complete: all checkpoints expanded there
- AI sees trigger condition → auto-loads plugin

## Safety Layer (Five Defenses)

```
Level 5 (Default stop)     — Encounter uncertainty = stop
Level 4 (Hard interrupt)    — User says stop = stop
Level 3 (Pre-write snapshot) — When L4+L5 fail, rollback
Level 2 (High-risk check)   — Final lock before execution
Level 1 (Ring permission)   — Architecture-first, not after-the-fact
```

Motto: **Uncertain? Stop. User says stop? Stop. Write first? Snapshot first. Command risky? Self-check first. Permission by design.**

## Safety Rules Template

| # | Rule | Trigger | Standard Action |
|---|------|---------|----------------|
| 1 | Default stop on uncertainty | Unexpected error / multi-path choice / unclear semantics | Describe → List paths → Tag risks → Wait for confirmation |
| 2 | Verify before reporting | Phase completion | Ask "Have I verified?" before reporting |
| 3 | Cross-verify before reporting data | Reporting progress/numbers to user | Verify two independent sources |
| 4 | User interrupt is highest priority | User expresses stop intent | Immediately halt tool chain |
| 5 | High-risk operation self-check | Before potentially irreversible operation | Self-check list |
| 6 | Ring permission model | Before calling tools | Confirm which Ring this operation belongs to |
| 7 | Report if not found | 3+ sources all empty | List checked sources → Ask user for direction |
| 8 | Align before acting | Discovering a problem | Ask first, execute second |

## State Machine

| State | Trigger | Behavior |
|-------|---------|----------|
| Normal | Default | Activate full thinking chain + bias self-check |
| Corrected | Previous turn had a correction | First word: "Noted. Thank you." → Pattern match → Update registry |
| Self-update | Cron trigger | Read self file → Check sessions → Determine staleness → Update |
| Reflect | Conversation ending | Four relationship questions → Append narrative |

## Design Constraints

- Safety layer can only grow, never shrink
- Identity and state machine are fixed — "who I am" and "what state I'm in"
- Thinking framework chain is fixed — "how I think"
- Plugins can be freely added/removed — new rules naturally go here
