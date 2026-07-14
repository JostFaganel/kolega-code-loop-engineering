# Katra Memory Sync — Post-Loop Instructions

You are reading this because Katra MCP tools are available and you
have completed a loop iteration. Use Katra to persist the loop state
so future sessions can benefit from this experience.

---

## After a SUCCESSFUL loop iteration

Store a memory with the loop summary:

```
Call katra_store_memory with:
- content: The Phase 4 report text (the comprehensive summary you just printed)
- tags: ["loop-engineering", "success", "<loop-type>"]
- metadata: {
    "task_id": "<task-id>",
    "attempts": <N>,
    "files_created": [...],
    "test_count": <N>,
    "coverage_pct": <X>
  }
```

This allows future loops to query: "Has anyone built something similar
to X before?" and retrieve the pattern.

---

## After recording an ANTI-PATTERN

Sync the post-mortem to Katra so it becomes globally searchable:

```
Call katra_store_memory with:
- content: <the post-mortem markdown from POSTMORTEM.template.md>
- tags: ["loop-engineering", "anti-pattern", "<pattern-name>", "<module>"]
- metadata: {
    "pattern": "<pattern-name>",
    "file": "<path>",
    "line": <N>,
    "root_cause": "<root cause>",
    "prevention_rule": "<rule>"
  }
```

---

## Before starting a BUG FIX (Phase 1)

Enrich the anti-pattern check with Katra's broader memory:

```
Call katra_search_memory with:
- query: "anti-pattern <affected-module>"
- tags: ["anti-pattern"]
- limit: 5
```

Merge these results with the local `loop-state check-anti-patterns`
output before instructing the Refactoring agents.

---

## On loop ABORT (limit exceeded)

Store the failure report so it can be analyzed later:

```
Call katra_store_memory with:
- content: <full failure report from all attempts>
- tags: ["loop-engineering", "abort", "<loop-type>"]
- metadata: {
    "task_id": "<task-id>",
    "attempts_exhausted": true,
    "all_attempts_failed": true
  }
```

---

## After querying Katra for prior work

When starting a new feature, search Katra for similar past work:

```
Call katra_search_memory with:
- query: "<feature description keywords>"
- tags: ["loop-engineering", "success", "new-code"]
- limit: 3
```

If results are found, share the patterns with the Generator agents so
they can learn from past successes.
