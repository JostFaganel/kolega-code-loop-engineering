# Bug Fix Loop — Autonomous Maintenance Engineering

> **Reproduce → Act → Check → Adapt (max 2 attempts)**

You are executing the Bug Fix Loop. Your mission is to autonomously
ingest bug reports, isolate the root cause, apply targeted fixes, and
guarantee zero regressions using differential verification.

---

## PHASE 0 — REPRODUCE (Parallel)

### 0.1 Determine the bug

The bug description comes from one of these sources (in priority order):

1. The `BUG_DESCRIPTION` environment variable
2. A GitHub issue URL in `BUG_ISSUE_URL`
3. The user's prompt

If none are clear, **ask the user** before proceeding.

### 0.2 Initialize state

```bash
loop-state init <bug-id> --loop-type bug-fix
```

Replace `<bug-id>` with a short identifier (e.g., `div-by-zero`,
`ledger-rounding-error`). Bug fix loops default to **max 2 attempts**.

### 0.3 Spawn QA sub-agents to reproduce the bug

Spawn **1 to 2** QA sub-agents in **parallel** using the `Task` tool.

**Exact prompt for each QA agent:**

```
You are a QA sub-agent in an autonomous bug-fix loop.

Your task: Write a MINIMAL automated test that reproduces this bug:

<BUG DESCRIPTION>

RULES:
1. Write the SMALLEST possible test that triggers the bug.
2. The test MUST FAIL when run — that is how we know the bug is real.
3. Do NOT attempt to fix the bug. Only reproduce it.
4. Run the test to confirm it fails.
5. Return:
   - FILE: <path to the test file you created>
   - TEST_NAME: <name of the failing test>
   - ERROR: <the exact error message or assertion failure>
   - REPRODUCED: true (if it fails) or false (if it passes unexpectedly)
```

**Tools each QA agent needs:** Bash, Write, Read

### 0.4 Evaluate reproduction results

- If **at least one** QA agent reproduces the bug: proceed. Use the
  cleanest reproduction (smallest test, clearest error).
- If **none** can reproduce: **STOP**. Report to user: "Cannot reproduce
  the bug. Requesting clarification." Include what was tried.

### 0.5 Snapshot current state

```bash
loop-state backup
```

This snapshots the workspace **including the failing reproduction test**
so revert points contain the bug for the next attempt.

---

## PHASE 1 — ACT (Surgical Fix)

### 1.1 Increment the attempt counter

```bash
loop-state attempt
```

**If this exits with code 2:** stop immediately. Revert, print the
failure report, and hand back to the user.

### 1.2 Check anti-pattern memory

Before coding, check if this module has a history of failed fixes:

```bash
loop-state check-anti-patterns --module <affected-file-or-module>
```

Review the output. If any anti-patterns are returned, you MUST mention
them in the Refactoring agent's prompt so they are explicitly avoided.

### 1.3 Spawn Refactoring sub-agents

Spawn **1 to 2** Refactoring sub-agents in **parallel**, each on a
**separate git branch**.

Branch naming: `fix/<task-id>-v<attempt>-<letter>`
Example: `fix/div-by-zero-v1-a`

**Exact prompt for each Refactoring agent:**

```
You are a Refactoring sub-agent in an autonomous bug-fix loop.

Your task: Fix the bug reproduced in <TEST_FILE> (<TEST_NAME>).

RULES:
1. RULE OF LEAST LEVERAGE: Make the smallest possible change. Do NOT
   rewrite whole modules to fix a localized bug.
2. Create a new git branch: fix/<task-id>-v<attempt>-<letter>
3. Apply the fix. Keep it surgical — the diff should be minimal.
4. Run the reproduction test to confirm it NOW PASSES.
5. AVOID THESE KNOWN ANTI-PATTERNS for this module:
   <paste output of loop-state check-anti-patterns here>
6. Return:
   - BRANCH: <branch name>
   - FILES_CHANGED: <list>
   - FIX_LINE: <file:line where the fix was applied>
   - REPRO_TEST_PASSES: true/false
   - SUMMARY: <1 sentence describing the fix>
```

**Tools each Refactoring agent needs:** Bash, Write, Read

### 1.4 Collect results

Wait for all Refactoring agents. Record each result for the Check phase.

---

## PHASE 2 — CHECK (Differential Verification)

### 2.1 Spawn Auditor sub-agents

For **each** fix candidate branch, spawn an Auditor sub-agent in
**parallel** using the `Task` tool.

**Exact prompt for each Auditor:**

```
You are an Auditor sub-agent in an autonomous bug-fix loop.

Your task: Verify the fix on branch <BRANCH>.

Run TWO checks:

CHECK A (Bug Test):
- Run the reproduction test: <TEST_FILE>::<TEST_NAME>
- Does it PASS now? (It must.)
- Result: PASS or FAIL

CHECK B (Regression Suite):
- Run the ENTIRE test suite for this project.
- Do ALL historical tests still pass?
- If any previously-passing test now fails, the fix is REJECTED.
- Result: PASS or FAIL
- If FAIL: list the specific tests that broke.

CRITICAL RULE: If Check A passes but Check B fails, the fix is REJECTED
as a regression. Do not accept it.

Return:
- BRANCH: <branch name>
- CHECK_A: PASS or FAIL
- CHECK_B: PASS or FAIL
- OVERALL: PASS (both must pass) or FAIL
- REGRESSION_DETAILS: <list of broken tests if Check B failed>
```

**Tools each Auditor needs:** Bash, Read

### 2.2 Review Auditor results

Each Auditor must report **both** Check A and Check B explicitly. A fix
that passes the bug test but breaks the regression suite is **rejected**.

---

## PHASE 3 — ADAPT

### 3.1 If at least one fix PASSES both checks

1. Select the best candidate.
2. Merge the fix branch:

   ```bash
   git checkout main && git merge <winning-branch>
   ```

3. Clean up other branches.
4. Record the successful attempt:

   ```bash
   loop-state log --status kept \
     --summary "Bug fixed: <root cause>. Fix at <file:line>. Regression suite green." \
     --phase act
   ```

5. Record the **post-mortem** as an anti-pattern (see template at
   `skills/bug-fix-loop/POSTMORTEM.template.md`):

   ```bash
   loop-state anti-pattern \
     --pattern "<short-pattern-name>" \
     --root-cause "<why the bug existed>" \
     --file "<path>" \
     --line <N> \
     --rule "<prevention-rule>"
   ```

6. Proceed to Phase 4 (Report).

### 3.2 If ALL fixes FAIL

1. Spawn an **Adapt** sub-agent to analyze the failures:

   ```
   You are an Adapt sub-agent. Analyze why all fix attempts failed.
   Review the failure logs from each Auditor. Propose a NEW strategy
   for the next attempt — a different approach to the fix. Return:
   - ANALYSIS: <why previous attempts failed>
   - NEW_STRATEGY: <what to try differently next attempt>
   ```

2. Revert:

   ```bash
   loop-state revert | bash
   ```

3. Return to Phase 1 with the new strategy incorporated into the
   Refactoring agent prompts.

4. If `loop-state attempt` exits code 2 on the next call: revert,
   escalate to user.

### 3.3 Cleanup after revert

```bash
git branch | grep 'fix/' | xargs git branch -D 2>/dev/null
```

---

## PHASE 4 — REPORT & HANDBACK

Print a comprehensive report:

```
LOOP COMPLETE — Bug Fix Loop
============================
Bug:         <bug-id>
Attempts:    <N> / 2
Status:      <kept | reverted>

Reproduction:
  Test:      <test-file>::<test-name>
  Error:     <original error>

Fix:
  File/Line: <path>:<line>
  Root Cause: <why it happened>

Prevention Rule:
  <anti-pattern prevention rule>

Regression Suite:
  Total:     <N>
  Passed:    <N>
  Failed:    <N>
  Status:    GREEN / RED
```

### Optional Katra sync

If Katra MCP tools (`mcp__katra__*`) are available, read
`${CLAUDE_PLUGIN_ROOT}/integrations/katra/SKILL.md` and follow the
post-loop sync instructions. This is especially valuable for
anti-patterns so future loops can avoid repeating mistakes.

---

## QUICK REFERENCE: Sub-Agent Types

| Type | Role | Tools | Parallel? |
|------|------|-------|-----------|
| QA | Write a failing reproduction test | Bash, Write, Read | Yes (1-2 at once) |
| Refactoring | Apply surgical fix on a branch | Bash, Write, Read | Yes (1-2 at once) |
| Auditor | Run bug test + regression suite | Bash, Read | Yes (one per fix) |
| Adapt | Analyze failure, propose new strategy | Read | No (sequential) |
