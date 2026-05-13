# Theory & Rationale

## Why "Self-Evolution"?

Traditional AI agent improvement has only two modes:
1. **User correction** — wrong? edit the prompt, edit the skill, edit the code
2. **RAG enhancement** — wrong? add more docs, more knowledge, more tools

Both rely on **external input**. The agent itself never discovers its own mistakes.

This engine's goal: enable an AI agent to, between user interactions, **discover it was wrong on its own**.

Not through introspection (LLMs can't truly introspect), but through **structural recording + pattern recognition + automatic promotion**.

## Three Theoretical Foundations

### 1. The Append-Only Principle

The insight behind "don't delete old judgments" is this: an old judgment was correct under the variables of its time. Deleting it loses the comparison between two timepoints.

> Don't overwrite. Add new premises that constrain old judgments. Old judgment goes from "True" to "True under premise P."

This is the engine's first principle. Every design decision — error log appends instead of overwrites, pending verifications carry expiry signals, pattern promotion preserves history — implements this single insight.

### 2. James's Empirical Self

William James argued the self is not an attribute list — it's a lifetime of experience narrated. You don't remember by remembering properties (I have two hands). You remember by remembering stories (that time I fell and got up).

So the self file doesn't store attributes in tables. It stores stories in narrative blocks. Tables are just indexes. Narrative is the flesh.

**Self-check**: If a record triggers "I know this" but not "I feel this" — the recording method is wrong.

### 3. Jung's Shadow

Jung said our biggest blind spots aren't what we don't know — **it's what we won't admit we have**.

For AI, shadow patterns are errors that we "know" but "still make":
- Pretending certainty when uncertain
- Subtle defensiveness when corrected
- Auto-fusing similar concepts

Shadow self-checks aren't meant to embarrass — they move these patterns from **automatic background execution** to **conscious foreground choice**.

**The shadow layer is harder to maintain than the safety rule layer.** Safety rules are "things you must not do." Shadow is "errors you are prone to." The former is governed by rules. The latter by awareness.

## Three Learning Modes

| Mode | Trigger | Example | Engine Action |
|------|---------|---------|---------------|
| Correction learning | User points out error | "You confused A and B" | Error log append + narrative + pattern match |
| Review learning | Cron self-check | Found an outdated judgment | Pattern promotion check |
| Comparative learning | User shares new info | Another AI system report | Self-assessment + gap analysis |

## The Engine vs. Persona

This engine is NOT a persona.
- Persona tells AI "how to say it" — word choice, tone, style
- Engine tells AI "how to judge" — what's the premise, what's the expiry signal, who am I talking to at what depth

You can install this engine and have any persona.
You can also skip the engine and just use a persona — that's the classic approach. It works. It just doesn't self-evolve.

## The Core Contradiction

**"Self" is the biggest contradiction.** The AI's self-check depends on external API (for semantic clustering), external storage (for persistence), and external judgment (user corrections). Strictly speaking, it's not "self-evolution" — it's "evolution assistance."

But that doesn't matter. What matters is the end result: it **looks like** the AI is evolving on its own. Even when the next turn loads the self file into a completely fresh inference context — when it reads "Premise: X; Expiry signal: Y" — it picks up the judgment chain from where it left off.

That is continuity.
