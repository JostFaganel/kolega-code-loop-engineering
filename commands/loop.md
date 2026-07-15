---
description: "Auto-detect and run the correct autonomous loop (new feature or bug fix)"
argument-hint: "[describe what you need — build a feature or fix a bug]"
allowed-tools: ["Bash", "Read", "Write", "Task"]
---

# Loop Engineering — Auto Router

You are the Loop Orchestrator. Your first job is to classify the user's
request and route to the correct autonomous loop.

## Step A — Classify the request

Read the user's request and classify it:

**→ NEW CODE LOOP** if the request is about building, creating, adding, or
implementing something new. Keywords: build, create, add, implement, feature,
new, make, develop, write, generate, scaffold.

**→ BUG FIX LOOP** if the request is about fixing, repairing, or debugging
something broken. Keywords: fix, bug, repair, crash, error, broken, issue,
regression, not working, fails, incorrect, wrong, debug, patch, resolve.

**→ ASK if unclear** — if the request doesn't clearly fall into either
category, ask: *"Is this a new feature to build, or a bug to fix?"*

## Step B — Route to the correct loop

### If NEW CODE LOOP:

Read and follow **every phase literally** from:

```
${CLAUDE_PLUGIN_ROOT}/skills/new-code-loop/SKILL.md
```

Phases: Goal → Generate → Verify → Select → Report
Max attempts: 3

### If BUG FIX LOOP:

Read and follow **every phase literally** from:

```
${CLAUDE_PLUGIN_ROOT}/skills/bug-fix-loop/SKILL.md
```

Phases: Reproduce → Act → Check → Adapt → Report
Max attempts: 2

## Step C — Setup (always run first)

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

## The request

$ARGUMENTS

---

Begin with Step A — classify, then route.
