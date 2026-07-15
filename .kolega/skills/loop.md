# Loop Engineering — Auto Router

> **Auto-detected skill.** You are the Loop Orchestrator. Classify the
> user's request and execute the correct autonomous loop with parallel
> sub-agents and strict keep-or-revert rules.

---

## Step A — Find the loop engineering repo

This skill is a bridge. You need the full repo to proceed. Find it:

1. First, check if this skill file is a symlink and resolve it:

```bash
LOOP_REPO=$(dirname "$(readlink -f "$0")" 2>/dev/null || echo "")
```

2. If that fails, search for the repo:

```bash
LOOP_REPO=$(find /home -maxdepth 4 -path "*/kolega-code-loop-engineering/.kolega/skills/loop.md" 2>/dev/null | head -1 | xargs dirname 2>/dev/null | sed 's|/.kolega/skills||')
```

3. If you find it, set the variable. If not, clone it:

```bash
if [ -z "$LOOP_REPO" ]; then
  git clone https://github.com/JostFaganel/kolega-code-loop-engineering.git /tmp/kolega-code-loop-engineering
  LOOP_REPO=/tmp/kolega-code-loop-engineering
fi
```

4. Install the state manager:

```bash
cd "$LOOP_REPO" && pip install -e .
```

## Step B — Classify the request

Read the user's request. Classify it:

**→ NEW CODE LOOP** if the request is about building, creating, adding,
or implementing something new. Keywords: build, create, add, implement,
feature, new, make, develop, write, generate, scaffold.

**→ BUG FIX LOOP** if the request is about fixing, repairing, or
debugging something broken. Keywords: fix, bug, repair, crash, error,
broken, issue, regression, not working, fails, incorrect, wrong, debug,
patch, resolve.

**→ If unclear**, ask: *"Is this a new feature to build, or a bug to fix?"*

## Step C — Route to the full loop

Based on the classification, read:

| If | File |
|----|------|
| New feature | `${LOOP_REPO}/skills/new-code-loop/SKILL.md` |
| Bug fix | `${LOOP_REPO}/skills/bug-fix-loop/SKILL.md` |

Follow every phase **literally**. Do not skip phases.

## Step D — Katra (if available)

After the loop completes, if Katra MCP tools (`mcp__katra__store_memory`,
`mcp__katra__search_memories`) are available, read:

```
${LOOP_REPO}/integrations/katra/SKILL.md
```

---

**Begin now.** Classify the user's request, resolve the repo, install
the tools, and execute the loop.
