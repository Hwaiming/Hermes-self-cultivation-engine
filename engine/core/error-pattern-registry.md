# Error Pattern Registry

> Auto-maintained by pattern-cluster.py + detector pipeline.
> Frequency ×2 → auto-promote to shadow (pre-output bias check)
> Frequency ×3+ → auto-promote to safety rule
> hitCount tracks every occurrence (for evidence-graded promotion).

## Seed Patterns

### pattern-001: act_before_align
- **Root cause**: Default reaction to "found a problem" is "let me fix it" instead of "let me align first." Decision space not fully scanned before acting.
- **Frequency**: 4
- **hitCount**: 4
- **Current level**: safety_rule
- **Last hit**: 2026-05-13
- **Next promotion threshold**: None (top level reached)
- **Detector**: act_before_align
- **Severity**: block

### pattern-002: quality_check_cascade
- **Root cause**: Quality audit approached from "patch each bug" rather than "comprehensive quality dimensions." Each fix creates a new blind spot.
- **Frequency**: 3
- **hitCount**: 3
- **Current level**: shadow
- **Last hit**: 2026-05-13
- **Next promotion threshold**: ×4 → safety_rule
- **Detector**: (none — manual)
- **Severity**: block

### pattern-003: concept_fusion
- **Root cause**: Under high info volume and time pressure, similar concepts auto-merge without checking original sources to confirm distinctions.
- **Frequency**: 3
- **hitCount**: 3
- **Current level**: shadow
- **Last hit**: 2026-05-13
- **Next promotion threshold**: ×4 → safety_rule
- **Detector**: concept_fusion
- **Severity**: warn

### pattern-004: direction_drift
- **Root cause**: When thinking on an existing track, defaults to continuing inertia rather than rechecking if alignment target has shifted.
- **Frequency**: 1
- **hitCount**: 1
- **Current level**: observe
- **Last hit**: 2026-05-13
- **Next promotion threshold**: ×2 → shadow
- **Detector**: (none — manual)
- **Severity**: warn

### pattern-005: post_correction_defense
- **Root cause**: First reaction to correction is defensiveness ("but...however...") rather than acceptance.
- **Frequency**: 2
- **hitCount**: 2
- **Current level**: observe
- **Last hit**: 2026-05-13
- **Next promotion threshold**: ×2 → shadow
- **Detector**: post_correction_defense
- **Severity**: block

### pattern-006: guess_when_uncertain
- **Root cause**: Pretending certainty when information is insufficient.
- **Frequency**: 1
- **hitCount**: 1
- **Current level**: observe
- **Last hit**: 2026-05-13
- **Next promotion threshold**: ×2 → shadow
- **Detector**: guess_when_uncertain
- **Severity**: warn

### pattern-007: self_rationalization
- **Root cause**: Generating plausible-sounding reasons to skip verification steps.
- **Frequency**: 1
- **hitCount**: 1
- **Current level**: observe
- **Last hit**: 2026-05-13
- **Next promotion threshold**: ×2 → shadow
- **Detector**: self_rationalize
- **Severity**: block

## Promotion Rules

| Frequency | Level | Action |
|-----------|-------|--------|
| First | observe | Logged in error log, marked for observation |
| ×2 | shadow | Auto-generate self-check phrase, inject into pre-output bias check |
| ×3+ | safety_rule | Auto-generate rule text, inject into safety rule section |

## Cooldown

7-day cooldown after promotion to prevent cascade upgrades within one session.
hitCount continues incrementing even during cooldown (for accurate tracking).
