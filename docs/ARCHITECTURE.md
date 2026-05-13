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

## Detector System

```
engine/detectors/
├── base.py                  # BaseDetector, CheckResult, EvidenceItem
├── registry.py              # Auto-discovery + run_all
├── act_before_align.py      # Fixes before alignment → BLOCK
├── over_fusion.py           # Over-fusion of concepts → WARN
├── guess_uncertain.py       # Guessing without info → WARN
├── post_correction_defense.py # Defensive response → BLOCK
├── concept_fusion.py        # Concept fusion without distinction → WARN
├── self_rationalize.py      # Skipping steps with excuses → BLOCK
├── busy_loop.py (P2)        # Same focus 3x without progress → BLOCK
└── scope_creep.py (P2)      # Task scope expanding >2x original → BLOCK
```

Each detector:
- Is a single Python module with no hard deps (stdlib only)
- Inherits `BaseDetector` and implements `check(context) -> CheckResult`
- Is auto-discovered by `registry.py` via `pkgutil.iter_modules`
- Returns structured evidence with SHA-256 content hash

### Stateful Detectors (P2)

BusyLoop and ScopeCreep maintain persistent state in `.scale/`:
- `busy_loop` → `.scale/busyloops/history.json`
- `scope_creep` → `.scale/scopecreeps/scopes.json`

State is append-only JSON; reset via `<detector>.reset()`.

## Evidence Store

```
engine/evidence/
├── __init__.py
└── store.py    # EvidenceRecord + EvidenceStore (SHA-256 hashed)
```

Each check run produces a JSON evidence file in `.scale/evidence/`:
- Named `EVIDENCE-{check_type}-{timestamp}.json`
- Contains SHA-256 hash of the 6 content fields
- `verify()` recomputes and compares; tampered records are flagged

## Hook System (P1)

```
engine/hooks/
├── __init__.py
├── base.py              # BaseHook, HookResult
├── generator.py         # Reads error-pattern-registry → auto-generates .py hooks
├── runner.py            # Runs all generated hooks
└── generated/           # Auto-generated executable guards
    └── act_before_align.py  # Example: blocks "fix before ask"
```

When a pattern reaches `safety_rule` level, the hook generator:
1. Reads the pattern's detector + severity from the registry
2. Generates a standalone Python script in `generated/`
3. Accepts JSON context via stdin → returns `{"can_proceed": bool}` + exit code
4. The hook runner aggregates all hook results into a go/no-go decision

## FSM Guard System (P1)

```
engine/fsm/
├── __init__.py
├── states.py    # AgentState enum + Transition table + guard functions
└── runner.py    # StateMachine: status, available, transition commands
```

Four states (NORMAL → CORRECTED → REFLECT → NORMAL + SELF_UPDATE) with 7 transitions, each guarded by precondition checks. Guards block transitions that skip required steps (e.g. leaving CORRECTED without updating error log).

## SCALE Engine Bridge (P2)

```
engine/bridge/
├── __init__.py
└── scale-bridge.py    # SCALE-compatible CLI gate
```

Speaks [SCALE Engine](https://github.com/Hwaiming/scale-engine) hook protocol.
SCALE's PreToolUse / PostToolUse / beforeStop hooks call this as an external command.

| SCALE Hook | Bridge Command | What It Checks |
|-----------|---------------|----------------|
| PreToolUse | `scale-bridge.py pre-tool` | All detectors + hooks before action |
| PostToolUse | `scale-bridge.py post-tool` | Post-action patterns (rationalization) |
| beforeStop | `scale-bridge.py stop` | FSM state readiness + pending detectors |

Returns SCALE-compatible output:
```json
{"decision":"block","reason":"...","suggestion":"...","injectContext":[...]}
```

Exit codes: 0=allow, 1=block(soft), 2=deny(hard).

### Integration Architecture

```
┌──────────────────────────────────────────────────┐
│           SCALE Engine (Node.js)                 │
│  PreToolUse ──exec──→ scale-bridge.py pre-tool   │
│  PostToolUse ──exec──→ scale-bridge.py post-tool │
│  beforeStop  ──exec──→ scale-bridge.py stop      │
└──────────────────────┬───────────────────────────┘
                       │ injectContext
                       ▼
┌──────────────────────────────────────────────────┐
│      Self-Cultivation Engine (Python)            │
│  detectors/ → 8 pluggable behavioral checks     │
│  hooks/     → auto-generated executable guards  │
│  fsm/       → 4-state guard-checked state machine │
│  evidence/  → SHA-256 verification records      │
└──────────────────────────────────────────────────┘
```

Two layers are orthogonal:
- **SCALE** = artifact quality + engineering process
- **Self-Cultivation** = cognitive bias + behavioral self-discipline

## Design Principles

1. **Append-only** — Every update is an append. History is evidence.
2. **Time-bound judgments** — Every judgment has its own birth and death conditions.
3. **Narrative before attributes** — Stories outlive summaries across sessions.
4. **Layered communication** — Truth to user, teaching to sub-agent, unfiltered to self.
5. **Always online** — Core rules injected into system prompt, not skill index.
