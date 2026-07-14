# New Code Loop — Autonomous Feature Engineering

> **Generator → Verifier → Keep/Revert (max 3 attempts)**

You are executing the New Code Loop. Your mission is to implement a
feature from a requirements specification using parallel Generator and
Verifier sub-agents, with strict keep-or-revert rules.

---

## PHASE 0 — GOAL (The Blueprint)

### 0.1 Determine the feature spec

The feature specification comes from one of these sources (in priority order):

1. The `FEATURE_SPEC` environment variable
2. A file the user pointed you at (e.g., a requirements doc, a GitHub issue)
3. The user's prompt

If none of these are clear, **ask the user** before proceeding.

### 0.2 Initialize state

```bash
loop-state init <feature-name> --loop-type new-code
```

Replace `<feature-name>` with a short, kebab-case identifier (e.g.,
`jwt-auth`, `ledger-reconciliation`).

### 0.3 Create the contract

Read `skills/new-code-loop/CONTRACT.template.md` and create a
`CONTRACT.md` file in the workspace. Fill in every section with
**specific, measurable** criteria:

- **Goal**: one sentence
- **Boundaries**: exactly what IS and IS NOT in scope
- **Success Criteria**: numbered, testable statements
- **Test Acceptance**: what tests must pass, coverage threshold

### 0.4 Snapshot current state

```bash
loop-state backup
```

This creates a revert point. If all attempts fail, the workspace will
be restored to this exact state.

---

## PHASE 1 — GENERATE (Parallel)

### 1.1 Increment the attempt counter

```bash
loop-state attempt
```

**If this exits with code 2:** stop immediately. Print the failure report
from all previous attempts and hand back to the user.

### 1.2 Spawn Generator sub-agents

Spawn **2 to 3** Generator sub-agents in **parallel** using the `Task`
tool. Each Generator must work on a **separate git branch** to avoid
conflicts.

Branch naming: `loop/<task-id>-v<attempt>-<generator-letter>`
Example: `loop/jwt-auth-v1-a`, `loop/jwt-auth-v1-b`

**Exact prompt for each Generator:**

```
You are a Generator sub-agent in an autonomous engineering loop.

Your task: Implement the feature described in CONTRACT.md.

RULES:
1. Create a new git branch: loop/<task-id>-v<attempt>-<letter>
2. Write the implementation code. Keep it modular and legible.
3. Write automated unit tests that cover the success criteria in CONTRACT.md.
4. Run the tests to confirm they pass.
5. Return a structured result with:
   - BRANCH: <branch name>
   - FILES: <list of files created/modified>
   - TESTS: <test count, pass count>
   - SUMMARY: <2-3 sentence summary of what you built>
```

**Tools each Generator needs:** Bash, Write, Read

### 1.3 Collect results

Wait for all Generators to finish. Record each result (branch name,
file list, test summary) for the Verify phase.

---

## PHASE 2 — VERIFY (Parallel)

### 2.1 Spawn Verifier sub-agents

For **each** Generator branch that produced code, spawn a Verifier
sub-agent in **parallel** using the `Task` tool.

**Exact prompt for each Verifier:**

```
You are a Verifier sub-agent in an autonomous engineering loop.

Your task: Grade the implementation on branch <BRANCH> against CONTRACT.md.

RUBRIC (all must pass for a PASS):
1. ALL TESTS PASS — run the full test suite on this branch
2. COVERAGE >= 80% — measure and report the exact percentage
3. CODE IS MODULAR AND LEGIBLE — no God objects, no 500-line functions
4. CONTRACT CRITERIA MET — verify each success criterion

Return a structured result:
- BRANCH: <branch name>
- RESULT: PASS or FAIL
- TEST_COUNT: <total>
- TEST_PASSED: <passed>
- COVERAGE_PCT: <percentage>
- ISSUES: <list of specific problems if FAIL, empty if PASS>
```

**Tools each Verifier needs:** Bash, Read

**CRITICAL**: Verifiers must report **numbers**, not subjective language.
"Coverage is 87%" — good. "Coverage looks decent" — reject and re-run.

### 2.2 Review Verifier results

Collect all Verifier reports. Identify which branches passed and which
failed.

---

## PHASE 3 — SELECT & KEEP/REVERT

### 3.1 If at least one branch PASSED

1. Select the best candidate (highest test coverage, fewest issues).
2. Merge that branch into the main branch:

   ```bash
   git checkout main && git merge <winning-branch>
   ```

3. Clean up other branches:

   ```bash
   git branch -D <losing-branch-1> <losing-branch-2>
   ```

4. Record the success:

   ```bash
   loop-state log --status kept \
     --summary "Feature implemented by <branch>. <tests> tests pass, <cov>% coverage." \
     --phase generate
   ```

5. Proceed to Phase 4 (Report).

### 3.2 If ALL branches FAILED

1. Revert to the last known-good state:

   ```bash
   loop-state revert | bash
   ```

   Verify the workspace is clean.

2. Return to Phase 1 (Generate) for the next attempt.

3. If this was attempt 3 and all failed, `loop-state attempt` will exit
   with code 2 on the next call — stop and escalate.

### 3.3 Cleanup after revert

After a revert, remove any leftover branches:

```bash
git branch | grep 'loop/' | xargs git branch -D 2>/dev/null
```

---

## PHASE 4 — REPORT & HANDBACK

Print a comprehensive report to the user:

```
LOOP COMPLETE — New Code Loop
=============================
Task:        <task-id>
Attempts:    <N> / <max>
Status:      <kept | reverted>

Artifacts:
  <file-1>
  <file-2>
  ...

Test Results:
  Total:   <N>
  Passed:  <N>
  Failed:  <N>
  Coverage: <X>%

Summary: <2-3 sentence summary of what was built>

Next: <recommended next task or "None — loop exhausted">
```

### Optional Katra sync

If Katra MCP tools are available, read `integrations/katra/SKILL.md`
and follow the post-loop sync instructions to persist this report.

---

## QUICK REFERENCE: Sub-Agent Types

| Type | Role | Tools | Parallel? |
|------|------|-------|-----------|
| Generator | Implements feature on a branch | Bash, Write, Read | Yes (2-3 at once) |
| Verifier | Runs tests, grades against rubric | Bash, Read | Yes (one per Generator) |
