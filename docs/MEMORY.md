# Hermes Memory System

> `engine/memory/` — retain, recall, reflect.

Lightweight persistent memory for AI agents. Works with Python stdlib + SQLite FTS5.
No Docker, no external services, no API keys.

Pairs with the **Self-Cultivation Engine**: detectors auto-retain their findings,
corrections auto-log as narrative, and the evidence store becomes searchable.

## Architecture

```
engine/memory/
├── __init__.py     # Public API: MemoryEngine
├── core.py         # retain/recall/reflect + session lifecycle
├── store.py        # SQLite + FTS5 backend (facts, events, sessions)
└── narrative.py    # Append-only narrative JSONL log (story-first)
```

### Three Memory Tiers

| Tier | Storage | Search | Lifespan | Use Case |
|------|---------|--------|----------|----------|
| **Facts** | SQLite key-value | Key prefix + tag match | Persistent, overwritable | User preferences, env facts, conventions |
| **Events** | SQLite + FTS5 | Full-text search | Persistent, append-only | Corrections, detector hits, key decisions |
| **Narrative** | JSONL (append-only) | Keyword scan | Persistent, never deleted | Stories, scenes, transformations |
| **Sessions** | SQLite + FTS5 | Full-text search | Persistent | Session summaries for cross-session recall |

## Quick Start

```python
from engine.memory.core import MemoryEngine

mem = MemoryEngine()

# Begin a session
mem.begin_session("session_001", title="Debugging auth flow")

# Retain a fact (structured knowledge)
mem.retain("language::Chinese", memory_type="fact", tags=["preference"])

# Retain an event (searchable)
mem.retain("Detector fired: act_before_align",
           context="correction", tags=["detector", "act_before_align"])

# Retain a narrative (story-first)
mem.retain(
    "User pointed out I was merging two concepts without checking sources",
    context="Now I always verify original sources first",
    memory_type="narrative",
    tags=["concept_fusion", "correction"],
)

# Search across all tiers
results = mem.recall("act_before_align")
# → {"facts": [...], "events": [...], "narratives": [...], "sessions": [...]}

# Synthesize across memories
reflection = mem.reflect("What correction patterns have occurred?")
# → {"correction_patterns": [...], "relevant_insights": [...], ...}

# End session
mem.end_session(summary="Fixed auth token expiry bug", token_count=1200)
```

## CLI Usage

```bash
# Check memory stats
python3 -m engine.check --memory

# Search memories
python3 -c "
from engine.memory.core import MemoryEngine
mem = MemoryEngine()
results = mem.recall('correction')
import json; print(json.dumps(results, indent=2, ensure_ascii=False))
"
```

## Integration with Self-Cultivation Engine

### Automatic retention on detector fire

When `engine/check.py` runs, failed detectors auto-retain as events:

```python
mem.capture_detector_result("act_before_align", passed=False,
                             message="Fixed before asking")
```

### Automatic correction narrative

The FSM's CORRECTED→REFLECT transition can call:

```python
mem.capture_correction(
    scene="User said 'ask before fixing'",
    transformation="Now I check existing solutions before proposing fixes"
)
```

### Cross-session continuity

Before each session, recall relevant history:

```python
prev = mem.recall("last session outcome", limit=3)
if prev["sessions"]:
    print(f"Previous session: {prev['sessions'][0]['summary']}")
```

## Retention Policy

| Tier | Auto-cleanup | Manual |
|------|-------------|--------|
| Facts | Never | `store.delete_fact(key)` |
| Events | FTS5 auto-managed | SQLite DELETE |
| Narrative | Never (append-only) | File rotation |
| Sessions | Never | SQLite DELETE |

## Design Notes

- **SQLite WAL mode** for concurrent reads during writes
- **FTS5 triggers** keep full-text index in sync automatically
- **Narrative JSONL** is append-only by design — story-first, never mutated
- **Facts** use UPSERT (INSERT ON CONFLICT UPDATE) — latest wins
- **Zero external dependencies** — SQLite is stdlib since Python 3.x
- Hindsight-compatible protocol: `retain()` / `recall()` / `reflect()`
