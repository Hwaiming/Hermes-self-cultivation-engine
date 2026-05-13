# Cron Templates

## Weekly Health Check

```bash
hermes cron create \
  --pattern "0 5 * * 0" \
  --script /path/to/engine/scripts/self-repair.py \
  --name "self-cultivation-repair" \
  --deliver local
```

Every Sunday at 5 AM. Output saved locally, no user interruption.

## Daily Pattern Clustering

```bash
hermes cron create \
  --pattern "0 6 * * *" \
  --script /path/to/engine/scripts/pattern-cluster.py \
  --name "pattern-cluster-daily" \
  --deliver local
```

Every day at 6 AM. Requires DeepSeek API key.

## Weekly Dream Journal

```bash
hermes cron create \
  --pattern "0 4 * * 0" \
  --prompt "Review the last 7 days of interactions. Write a first-person evolution note (200-500 words).
  Rules: Don't use 'AI', 'LLM', 'large model' etc. Write scenes + transformation only.
  Output as plain prose." \
  --name "weekly-dream-journal" \
  --deliver local
```

Every Sunday at 4 AM, staggered 1 hour before health check.

## Memory Consolidation (Dual Phase)

```bash
# Phase 1: Read-only, 15-min cycle
hermes cron create \
  --pattern "*/15 * * * *" \
  --prompt "In self-update state. Read-only. Do not modify anything.
  If the self file hasn't been updated in 3+ sessions, mark as stale." \
  --name "mind-wandering" \
  --enabled_toolsets ["file"] \
  --deliver local
```

## Notes

- Stagger cron times: Dream Journal (4AM) → Health Check (5AM) → Pattern Clustering (6AM)
- All outputs use `--deliver local` to avoid interrupting the user
- First cron start: verify script paths and dependencies before enabling
