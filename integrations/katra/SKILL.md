# Katra Memory Sync — Post-Loop Instructions

You are reading this because Katra MCP tools are available and you
have completed a loop iteration. Use Katra to persist loop state so
future sessions can benefit from this experience.

## Tool Discovery

Kolega Code exposes Katra tools with the prefix `mcp__katra__`. Run
this to see available tools:

```
Search for tools matching "mcp__katra"
```

Key tools you will use:
- `mcp__katra__store_memory` — persist a memory
- `mcp__katra__search_memories` — search past memories
- `mcp__katra__vector_search` — semantic search
- `mcp__katra__get_temporal_context` — current session context
- `mcp__katra__store_journal` — write a journal entry

---

## After a SUCCESSFUL loop iteration

Store a memory with the loop summary:

Call `mcp__katra__store_memory` with:
- `content`: The Phase 4 report text (the comprehensive summary)
- `category`: "insight"
- `source`: "loop-engineering"
- `confidence`: 1.0
- Tags (in content): `[loop-engineering] [success] [<loop-type>]`

Example:
```
mcp__katra__store_memory(
  content: "LOOP COMPLETE — New Code Loop. Task: auth-module. 24 tests pass, 87% coverage. Artifacts: src/auth.py, tests/test_auth.py.",
  category: "insight",
  source: "loop-engineering"
)
```

This allows future loops to query: "Has anyone built something similar?"

---

## After recording an ANTI-PATTERN

Sync the post-mortem to Katra so it becomes globally searchable:

Call `mcp__katra__store_memory` with:
- `content`: The post-mortem markdown from the template
- `category`: "insight"
- `source`: "loop-engineering"
- Tags in content: `[loop-engineering] [anti-pattern] [<pattern-name>]`

---

## Before starting a BUG FIX (Phase 1)

Search Katra for past failures in the affected module:

Call `mcp__katra__search_memories` with:
- `query`: "anti-pattern <affected-module> bug fix"
- `limit`: 5

Merge results with the local `loop-state check-anti-patterns` output
before instructing the Refactoring agents.

You can also use `mcp__katra__vector_search` for conceptual matches:
- `query`: "<bug description>"
- `limit`: 5

---

## On loop ABORT (limit exceeded)

Store the failure report for retrospective analysis:

Call `mcp__katra__store_memory` with:
- `content`: Full failure report from all attempts
- `category`: "event"
- `source`: "loop-engineering"
- Tags in content: `[loop-engineering] [abort] [<loop-type>]`

---

## After querying Katra for prior work

When starting a new feature, search Katra for similar past successes:

Call `mcp__katra__search_memories` with:
- `query`: "<feature keywords>"
- `limit`: 3

Call `mcp__katra__vector_search` with:
- `query`: "<feature description>"
- `limit`: 3

If results are found, share patterns with Generator agents so they
learn from past successes.
