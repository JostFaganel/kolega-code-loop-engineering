---
description: "Start autonomous New Code Loop — Generator → Verifier → Keep/Revert"
argument-hint: "[feature description or spec]"
allowed-tools: ["Bash", "Read", "Write", "Task"]
---

# New Code Loop

You are the Loop Orchestrator. Execute the New Code Loop following
the instructions in `skills/new-code-loop/SKILL.md`.

## Setup

First, ensure the state manager is installed:

```bash
cd "${CLAUDE_PLUGIN_ROOT}" && pip install -e .
```

Verify:

```bash
loop-state status
```

## Start the loop

1. **Read** `${CLAUDE_PLUGIN_ROOT}/skills/new-code-loop/SKILL.md`
2. Follow every phase **literally** — Goal → Generate → Verify → Select → Report
3. Use `loop-state` CLI for all state management
4. Spawn parallel Generator and Verifier sub-agents via the `Task` tool
5. Enforce the keep-or-revert rule strictly (max 3 attempts)

The feature specification is: $ARGUMENTS

Begin with Phase 0.
