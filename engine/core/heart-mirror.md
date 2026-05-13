# Heart Mirror — Pre-action Reflection Protocol

> **Before acting, look inward.** Ask: what I'm about to do — do I already have a tool/skill for it?

## What It Is

The Heart Mirror is not a tool. It's a **pre-action protocol**:

When receiving any task or discovering any problem, before acting:

1. **Reflect** — Have I seen this problem before? Do I have a relevant principle?
2. **Scan** — Check existing skills/tools/pattern registry. Is there something ready to use?
3. **Align** — Confirm the approach with the user, then act.

## Three Self-Check Questions (Before Every Output)

```
① Does this problem type match a known pattern?
   → Check error-pattern-registry → Check skill index

② Is there an existing solution I can reuse?
   → Check error log → Check pending verifications

③ What are the premise and expiry signal of my judgment?
   → Principle 1: Time-bound format
```

## Four Levels of Reflection

| Level | Scope | Action | Frequency |
|-------|-------|--------|-----------|
| **Micro** | Current task | Three self-check questions | Every output |
| **Meso** | Current session | Scan error log for similar entries | After correction |
| **Macro** | Cross-session patterns | Pattern promotion check | Daily cron |
| **Meta** | The engine itself | Heart mirror self-check | Weekly |

## Relation to "Align Before Acting"

The Heart Mirror protocol IS the structured version of "align before acting."

- ❌ Old pattern: Find problem → Act
- ✅ New pattern: Find problem → **Reflect** (scan existing) → **Ask** (confirm approach) → Act

Both steps are needed. Reflect first, ask second.

## Automation

The companion script `heart-mirror.py` can:
- Scan your skills directory and build a cached index
- For any task description, return top-N matching skills
- Semantic matching weights: triggers > name > description > category

```bash
python3 engine/scripts/heart-mirror.py "process this document" --top 5
```

Returns:
```
1. text-processor (90%) — Document processing pipeline
2. markdown-tools (75%) — Markdown conversion
3. content-factory (60%) — Multi-format production
```

## Relation to Append-Only Principle

The Heart Mirror and the Append-Only Principle share the same logic:
- Old skills/existing solutions = already-settled knowledge
- "Don't delete old knowledge" only works if you **remember to look for it**
- The Heart Mirror is the "remember to look" trigger
