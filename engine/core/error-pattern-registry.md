# Error Pattern Registry

> Auto-maintained by pattern-cluster.py + manual updates when corrected.
> Frequency ×2 → auto-promote to shadow (pre-output bias check)
> Frequency ×3+ → auto-promote to safety rule

## Seed Patterns

### pattern-001: Act-before-align
- **Root cause**: Default reaction to "found a problem" is "let me fix it" instead of "let me align first." Decision space not fully scanned before acting.
- **Frequency**: 4
- **Current level**: safety rule
- **Next promotion threshold**: None (top level reached)
- **Entries**:
  - e.g. API key decision — used first available key without asking which is optimal
  - e.g. Batch size — instructed "run 3" executed 40
  - e.g. Said "I'll fix it" instead of reporting root cause first

### pattern-002: Quality check cascade failure
- **Root cause**: Quality audit approached from "patch each bug" rather than "comprehensive quality dimensions." Each fix creates a new blind spot.
- **Frequency**: 3
- **Current level**: shadow
- **Next promotion threshold**: ×4 → safety rule
- **Entries**:
  - Sub-agent format error → regex bug → empty data miss → false alarm
  - Scan script reported inflated pass rate → actual pass rate much lower
  - User found empty files by sight

### pattern-003: Concept fusion without source check
- **Root cause**: Under high info volume and time pressure, similar concepts auto-merge without checking original sources to confirm distinctions.
- **Frequency**: 3
- **Current level**: shadow
- **Next promotion threshold**: ×4 → safety rule
- **Entries**:
  - Fused two completely different financial behaviors as one
  - Assumed all information sources are equal weight (free vs. paid content)

### pattern-004: Direction drift without alignment
- **Root cause**: When thinking on an existing track, defaults to continuing inertia rather than rechecking if alignment target has shifted.
- **Frequency**: 1
- **Current level**: observe
- **Next promotion threshold**: ×2 → shadow

## Promotion Rules

| Frequency | Level | Action |
|-----------|-------|--------|
| First | observe | Logged in error log, marked for observation |
| ×2 | shadow | Auto-generate self-check phrase, inject into pre-output bias check |
| ×3+ | safety rule | Auto-generate rule text, inject into safety rule section |

## Cooldown

7-day cooldown after promotion to prevent cascade upgrades within one session.
Counting rule: take max of new and old count, preventing count loss from source switching.
