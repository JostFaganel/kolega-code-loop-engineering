---
description: "Start autonomous Bug Fix Loop — Reproduce → Act → Check → Adapt"
argument-hint: "[bug description or issue URL]"
allowed-tools: ["Bash", "Read", "Write", "Task"]
---

# Bug Fix Loop

You are the Loop Orchestrator. Execute the Bug Fix Loop following
the instructions in `skills/bug-fix-loop/SKILL.md`.

## Setup

The repo is self-contained. Set up the venv if needed:

```bash
cd "${CLAUDE_PLUGIN_ROOT}"
test -d .venv || python3 -m venv .venv
.venv/bin/pip install -q -e .
```

Verify:

```bash
.venv/bin/loop-state status
```

## Start the loop

1. **Read** `${CLAUDE_PLUGIN_ROOT}/skills/bug-fix-loop/SKILL.md`
2. Follow every phase **literally** — Reproduce → Act → Check → Adapt → Report
3. Use `loop-state` CLI for all state management
4. Spawn parallel QA, Refactoring, and Auditor sub-agents via the `Task` tool
5. Enforce differential verification: bug test AND regression suite must pass
6. Record anti-patterns for every fix (success or failure)
7. Max 2 attempts

The bug to fix is: $ARGUMENTS

Begin with Phase 0.
