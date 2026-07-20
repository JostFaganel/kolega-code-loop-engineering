# Bug Fix Loop — Autonomous Maintenance Engineering

> **Reproduce → Investigate → Act → Check → Adapt (max 2 attempts)**

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
.venv/bin/loop-state init <bug-id> --loop-type bug-fix
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
.venv/bin/loop-state backup
```

This snapshots the workspace **including the failing reproduction test**
so revert points contain the bug for the next attempt.

---

## PHASE 1 — INVESTIGATE (Broad Exploration)

> **Always runs. Never blocks. Does NOT consume an attempt.**
>
> Investigation is read-only. Investigators use Read, Bash, Glob only.
> No Write tool, no code changes, no branches.

### 1.1 Determine the investigation scope

| Attempt | Scope | Description |
|---------|-------|-------------|
| 1 (first run) | **NEIGHBORHOOD** | Affected module + adjacent modules + direct dependencies + recent git history |
| 2 (retry) | **As directed by ADAPT** | NEIGHBORHOOD or SYSTEM (see Phase 4) |

If this is a retry after ADAPT, check the Adapt agent's output for
`INVESTIGATION_SCOPE`. If it says `SYSTEM`, use SYSTEM scope. Otherwise
default to NEIGHBORHOOD.

If the Adapt agent did not specify a scope (malformed output), default
to **SYSTEM** — safer to go broader when uncertain on retry.

### 1.2 Check anti-pattern memory

Before investigating, check if this module has a history of failed fixes:

```bash
.venv/bin/loop-state check-anti-patterns --module <affected-file-or-module>
```

Review the output. Anti-patterns are injected into the Investigator
prompts so known-bad strategies are explicitly avoided.

### 1.3 Spawn Investigator sub-agents

Spawn **exactly 2** Investigator sub-agents in **parallel** using the
`Task` tool. Two investigators provide diversity of perspective.

**Exact prompt for each Investigator:**

```
You are an Investigator sub-agent in an autonomous bug-fix loop.

BUG:           <bug description>
TEST:          <test-file>::<test-name>
ERROR:         <error message from reproduction>

SCOPE:         <NEIGHBORHOOD | SYSTEM>

KNOWN ANTI-PATTERNS (do NOT propose these as strategies):
<output of loop-state check-anti-patterns, or "None recorded">

<If retry after ADAPT:>
PREVIOUS FAILURE ANALYSIS:
<Adapt agent's analysis from the failed attempt>
WHY SCOPE WAS ESCALATED (if SYSTEM): <Adapt agent's reasoning>

---

Your task: Conduct a TWO-PASS investigation. Pass 1 explores the system
broadly WITHOUT focusing on the bug. Pass 2 uses that understanding to
generate MULTIPLE fix hypotheses. Do NOT fix anything. Do NOT write code.

Your investigation SCOPE determines how far you reach. Follow the scope
exactly — do not go beyond it on NEIGHBORHOOD, do not stay narrow on
SYSTEM.

---

PASS 1 — BROAD SYSTEM UNDERSTANDING

Complete ALL of the following before moving to Pass 2. Do not trace the
error path yet. Understand the system first.

1A. ARCHITECTURE & CONVENTIONS
    - Read the module(s) implicated by the bug. What is their role in the
      system? What design patterns do they follow?
    - Read adjacent modules in the same package/directory. How do they
      interact? What are the boundaries?
    - Identify coding conventions: error handling style, validation
      patterns, state management approach, naming conventions.
    - What architectural assumptions does this code make? (e.g., "callers
      always validate inputs", "this is always called after init")
    - Read any README, docstrings, or design docs for this area.

1B. INTENDED BEHAVIOR
    - What is this code SUPPOSED to do? Find documentation, comments,
      commit messages, or related tests that describe the intended
      behavior.
    - Read related tests (not the repro test) — what scenarios were
      considered during development? What edge cases were tested?
    - Is there a specification, issue tracker description, or design
      doc that defines correct behavior?
    - Identify any gap between intended behavior and the reproduction
      test's expectations.

1C. RECENT CHANGES
    - Run `git log --oneline -20` on the affected files. Look for recent
      commits that modified the error area or adjacent code.
    - Run `git log -p --follow -10 <affected-file>` and skim the diffs.
      When was the code last changed and why?
    - Run `git blame` on the lines around the error site. Who last
      touched this code and in what commit?
    - Identify any recent refactors, feature additions, or dependency
      updates that might have introduced the bug.

1D. RELATED FEATURES & ANALOGOUS CODE
    - Find features/modules that are SIMILAR to the buggy one (same
      pattern, same layer, same responsibility). Read them.
    - How do those similar modules handle the same scenario? Are they
      doing something the buggy module isn't?
    - Are there tests in analogous modules that test the scenario the
      buggy module fails? What do they look like?
    - Flag any analogous code that might have the SAME class of bug.

<IF SCOPE IS "SYSTEM" — ALSO COMPLETE 1E–1M BELOW>

1E. GLOBAL STATE AUDIT
    - Search for ALL singletons, module-level variables, global objects,
      and process-wide state in the project.
    - For each: could it be mutated during the error path? Could stale
      or corrupted state explain the bug?
    - Check for initialization order issues — does the buggy code depend
      on state that might not be initialized yet?

1F. CROSS-CUTTING CONCERNS
    - Find all middleware, interceptors, decorators, hooks, filters,
      and aspect-oriented code in the project.
    - For each: could it execute around the buggy code and alter
      behavior? (e.g., a decorator that transforms return values, a
      middleware that modifies requests, an interceptor that swallows
      errors)
    - Read any framework-level configuration that wires these concerns.

1G. TRANSITIVE DEPENDENCY GRAPH
    - Expand the dependency map beyond direct callers/callees:
      - Callers of callers (who ultimately triggers this?)
      - Callees of callees (what's at the bottom of the stack?)
    - Trace ALL import/usages of the affected module across the ENTIRE
      project — not just local ones.
    - Build a full ripple map: if this code changes, what is the
      complete set of things that could be affected?

1H. CONFIGURATION SURFACE
    - Find ALL environment variables, config files (.env, .yaml, .json,
      .toml, .ini), feature flags, and CLI arguments in the project.
    - For each: could it influence the behavior of the buggy code?
    - Check for configuration that is set differently in test vs.
      production — could the bug only manifest in one environment?

1I. EXTERNAL DEPENDENCY AUDIT
    - Identify ALL external boundaries the buggy code touches: API
      clients, database connections, file system I/O, message queues,
      caches, third-party SDKs.
    - For each: what are the failure modes? Could the external system
      return unexpected data, timeout, or behave differently?
    - Check for missing error handling at any boundary.
    - Check for test mocks that might be hiding real behavior.

1J. EVENT & MESSAGE FLOW
    - Search for all pub/sub, event emitters, callbacks, websockets,
      message queues, polling loops, and reactive patterns.
    - Map the event flow: could an event trigger the buggy code
      asynchronously? Could the bug be a timing/ordering issue?
    - Check for events that fire during the error path but aren't
      visible in a synchronous stack trace.

1K. TEST INFRASTRUCTURE AUDIT
    - Read the test setup (fixtures, before/after hooks, mocks, stubs).
    - Could the bug be in the TEST, not the code? (Wrong expectations,
      stale fixtures, incorrect mocks, test ordering dependency)
    - Run the reproduction test in isolation vs. with the full suite —
      does behavior differ?
    - Check for flaky tests, shared mutable fixtures, or global test
      state that could cause false reproductions.

1L. FULL GIT HISTORY
    - Run `git log --all --follow -- <affected-files>`. Read the ENTIRE
      history of the affected logic, not just recent commits.
    - Look for: deleted code that was handling this case, refactors that
      changed assumptions, commits that added then removed related logic.
    - Run `git log -S"<key-function-or-variable>"` to find ALL commits
      that touched the relevant logic, even across file renames.

1M. SIDE EFFECT MAP
    - During the error path execution, what ELSE happens? Logging?
      Metrics emission? Cache writes? State mutations? File writes?
      Network calls?
    - For each side effect: could IT be the real problem? (e.g., a log
      statement that throws, a metric that corrupts state, a cache
      write that triggers eviction)
    - Build a sequential timeline of everything that happens from test
      entry to error — not just the code path, but all observable
      effects.

---

PASS 2 — MULTIPLE FIX HYPOTHESES

Now that you understand the system broadly, trace the error path and
generate MULTIPLE distinct fix hypotheses. Do NOT converge on one.

2A. ERROR PATH TRACE
    Starting from the reproduction test, trace the full execution path
    to the error. Use grep/ripgrep to follow function calls. Identify
    the exact point where correctness breaks. Determine whether the root
    cause is at the error site or upstream (bad caller data, missing
    initialization, violated precondition, race condition, etc.).

2B. UNEXPECTED ROOT CAUSE EXPLORATION
    Explicitly ask: "Could the root cause be somewhere unexpected?"
    - Could the bug be in a dependency, not this module?
    - Could it be a configuration issue, not a code bug?
    - Could it be a data/state issue (e.g., database inconsistency)?
    - Could multiple factors combine to cause the symptom?
    - What would the bug look like if it originated in a DIFFERENT module?
    List any alternative root cause candidates, even if low probability.

2C. GENERATE 2–3 FIX HYPOTHESES
    Based on Pass 1 and 2A–2B, generate 2–3 DISTINCT fix hypotheses.
    Each hypothesis must be a DIFFERENT approach, not variations of the
    same idea. For each hypothesis, provide:

    HYPOTHESIS <N>:
      APPROACH: <what to change and where — be specific: file:line>
      RATIONALE: <why this approach, grounded in Pass 1 findings>
      RISKS: <what could go wrong, what else might break>
      VERIFICATION: <what tests/checks would confirm this fix is correct>
      CONFIDENCE: HIGH | MEDIUM | LOW

    Ensure the hypotheses are genuinely different. Examples of distinct
    approaches:
    - Fix the symptom site vs. fix the upstream caller
    - Add a guard clause vs. change the data flow
    - Local patch vs. extract shared logic
    - Fix the code vs. fix the test expectations (if the test is wrong)

---

OUTPUT FORMAT — Return a structured diagnostic report:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PASS 1 — BROAD SYSTEM UNDERSTANDING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ARCHITECTURE & CONVENTIONS:
  <module roles, design patterns, boundaries, conventions, assumptions>

INTENDED BEHAVIOR:
  <what this code should do, sources of truth, spec gaps>

RECENT CHANGES:
  <relevant commits, blames, potential introduction points>

RELATED FEATURES & ANALOGUES:
  <similar modules, how they handle this, potential same-class bugs>

<If SCOPE was SYSTEM:>
GLOBAL STATE:
  <singletons, globals, module-level state, init order issues>

CROSS-CUTTING CONCERNS:
  <middleware, decorators, hooks, interceptors that affect this code>

TRANSITIVE DEPENDENCIES:
  <full ripple map: callers-of-callers, callees-of-callees>

CONFIGURATION SURFACE:
  <env vars, config files, feature flags that influence behavior>

EXTERNAL DEPENDENCIES:
  <API clients, DB, file I/O, message queues — boundaries and failure modes>

EVENT & MESSAGE FLOW:
  <pub/sub, callbacks, async triggers — anything invisible in sync trace>

TEST INFRASTRUCTURE:
  <test setup audit, fixture correctness, mock accuracy, flakiness>

FULL GIT HISTORY:
  <entire history of affected logic, deleted code, assumption changes>

SIDE EFFECT MAP:
  <timeline of everything that happens from test entry to error>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PASS 2 — FIX HYPOTHESES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ERROR PATH:
  <file>:<line> — <function> — <what happens>
  → ... → <error>

UNEXPECTED ROOT CAUSE CANDIDATES:
  - <alternative root cause, probability, why it could explain the bug>
  - ...

HYPOTHESIS 1:
  APPROACH: <file:line — what to change>
  RATIONALE: <why, grounded in Pass 1>
  RISKS: <what could break>
  VERIFICATION: <how to confirm>
  CONFIDENCE: HIGH | MEDIUM | LOW

HYPOTHESIS 2:
  APPROACH: <different approach>
  ...

HYPOTHESIS 3 (optional):
  APPROACH: <different approach>
  ...

OVERALL CONFIDENCE: HIGH | MEDIUM | LOW
```

**Tools each Investigator needs:** Read, Bash (grep/ripgrep/git/find), Glob — read-only. **No Write tool.**

### 1.4 Merge investigation results

Wait for both Investigators. Merge their reports into a single
**Diagnostic Brief**:

- If both converge on the same hypothesis as highest confidence →
  present it as the leading hypothesis, but include alternatives.
- If they disagree → present both perspectives equally, note the
  disagreement. This is valuable information.
- If one Investigator found something the other missed → highlight it.
- If both return LOW confidence → note it but proceed. Include everything.
- If one fails entirely → use the surviving report as-is.

**Key rule**: the merged Diagnostic Brief MUST retain all hypotheses from
both Investigators. Never discard alternatives. The Refactoring agent
needs options.

### 1.5 Fallback

If both Investigators fail entirely (timeout, error, empty output),
proceed to Phase 2 (ACT) without the diagnostic brief. Investigation
never blocks the loop.

---

## PHASE 2 — ACT (Surgical Fix)

### 2.1 Increment the attempt counter

```bash
.venv/bin/loop-state attempt
```

**If this exits with code 2:** stop immediately. Revert, print the
failure report, and hand back to the user.

### 2.2 Spawn Refactoring sub-agents

Spawn **1 to 2** Refactoring sub-agents in **parallel**, each on a
**separate git branch**.

Branch naming: `fix/<task-id>-v<attempt>-<letter>`
Example: `fix/div-by-zero-v1-a`

**Exact prompt for each Refactoring agent:**

```
You are a Refactoring sub-agent in an autonomous bug-fix loop.

Your task: Fix the bug reproduced in <TEST_FILE> (<TEST_NAME>).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DIAGNOSTIC BRIEF (from investigation phase)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SYSTEM CONTEXT:
<Pass 1 findings: architecture, intended behavior, recent changes, analogues>
<If SYSTEM scope: global state, cross-cutting concerns, transitive deps,
 config, external deps, events, test infra, full git history, side effects>

ERROR PATH:
<Pass 2 error trace>

FIX HYPOTHESES (2–3 distinct approaches — choose or combine):
<All hypotheses from both Investigators, with confidence levels>

UNEXPECTED ROOT CAUSE CANDIDATES:
<Alternative explanations to rule out>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RULES:
1. REVIEW ALL HYPOTHESES. You may choose the best one, combine elements
   from multiple hypotheses, or develop a new approach if none fit.
   Justify your choice in your summary.
2. RULE OF LEAST LEVERAGE: Make the smallest possible change. Do NOT
   rewrite whole modules to fix a localized bug.
3. Create a new git branch: fix/<task-id>-v<attempt>-<letter>
4. Apply the fix. Keep it surgical — the diff should be minimal.
5. After fixing, check the RISK areas from each hypothesis you
   considered. Run any tests in those areas to catch collateral damage
   early.
6. Run the reproduction test to confirm it NOW PASSES.
7. Run the VERIFICATION checks from your chosen hypothesis.
8. AVOID THESE KNOWN ANTI-PATTERNS for this module:
   <paste output of .venv/bin/loop-state check-anti-patterns here>
9. If your fix doesn't work, try a DIFFERENT hypothesis rather than
   iterating on a failing approach. Do not waste time on dead ends.
10. Return:
    - BRANCH: <branch name>
    - FILES_CHANGED: <list>
    - FIX_LINE: <file:line where the fix was applied>
    - HYPOTHESIS_USED: <which hypothesis you followed, or "combined" or "new">
    - REPRO_TEST_PASSES: true/false
    - RISK_AREA_CHECKS: <results from checking risk areas>
    - VERIFICATION_CHECKS: <results from verification targets>
    - SUMMARY: <1 sentence describing the fix and why this approach>
```

**Tools each Refactoring agent needs:** Bash, Write, Read

### 2.3 Collect results

Wait for all Refactoring agents. Record each result for the Check phase.

---

## PHASE 3 — CHECK (Differential Verification)

### 3.1 Spawn Auditor sub-agents

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

### 3.2 Review Auditor results

Each Auditor must report **both** Check A and Check B explicitly. A fix
that passes the bug test but breaks the regression suite is **rejected**.

---

## PHASE 4 — ADAPT

### 4.1 If at least one fix PASSES both checks

1. Select the best candidate.
2. Merge the fix branch:

   ```bash
   git checkout main && git merge <winning-branch>
   ```

3. Clean up other branches.
4. Record the successful attempt:

   ```bash
   .venv/bin/loop-state log --status kept \
     --summary "Bug fixed: <root cause>. Fix at <file:line>. Hypothesis: <HYPOTHESIS_USED>. Regression suite green." \
     --phase act
   ```

5. Record the **post-mortem** as an anti-pattern (see template at
   `skills/bug-fix-loop/POSTMORTEM.template.md`):

   ```bash
   .venv/bin/loop-state anti-pattern \
     --pattern "<short-pattern-name>" \
     --root-cause "<why the bug existed>" \
     --file "<path>" \
     --line <N> \
     --rule "<prevention-rule>"
   ```

6. Proceed to Phase 5 (Report).

### 4.2 If ALL fixes FAIL

1. Spawn an **Adapt** sub-agent to analyze the failures and decide on
   scope escalation:

   ```
   You are an Adapt sub-agent. Analyze why all fix attempts failed.

   CURRENT SCOPE: <NEIGHBORHOOD | SYSTEM>

   Review:
   1. The diagnostic briefs (Pass 1 system context + Pass 2 hypotheses)
   2. The failure logs from each Auditor
   3. The Refactoring agents' summaries (which hypothesis they chose)
   4. The known anti-patterns

   Determine:
   - Was the system understanding (Pass 1) accurate? If not, what was missed?
   - Which hypotheses were attempted and why did they fail?
   - Are there UNATTEMPTED hypotheses that should be tried?
   - Was the unexpected root cause exploration correct — did we miss the
     real root cause?
   - **CRITICAL — SCOPE DECISION**: Could the root cause lie OUTSIDE the
     current investigation scope? Consider:
     - Did all hypotheses fail in ways that suggest the real problem is
       elsewhere? (e.g., all fixes "work" but don't actually fix the
       symptom, or all fixes cause unrelated test failures)
     - Did the original investigation miss areas that now look relevant?
     - Is there evidence of global state, configuration, async behavior,
       or external dependency issues that the neighborhood scope didn't cover?
     - Did the bug SURVIVE a correct-looking fix? (strong signal the root
       cause is elsewhere)
   - Should we abandon ALL current hypotheses and reframe the problem?

   Return:
   - ANALYSIS: <why previous attempts failed, referencing investigation accuracy>
   - PASS_1_ACCURACY: <was the system understanding correct? yes|partial|no>
   - ABANDONED_HYPOTHESES: <which hypotheses are ruled out and why>
   - RETAINED_HYPOTHESES: <which hypotheses are still viable>
   - NEW_HYPOTHESIS: <if needed, a new approach not in the original set>
   - NEW_STRATEGY: <concise direction for the retry>
   - INVESTIGATION_SCOPE: NEIGHBORHOOD | SYSTEM
     Set to SYSTEM if the root cause may be outside the local neighborhood.
     Set to NEIGHBORHOOD if the existing investigation was sufficient and
     only the fix approach needs to change.
     DEFAULT: SYSTEM if previous scope was NEIGHBORHOOD and all fixes failed
     for reasons unrelated to the fix quality itself (e.g., "fix was correct
     but bug persisted").
   ```

2. Revert:

   ```bash
   .venv/bin/loop-state revert | bash
   ```

3. Return to Phase 0 (REPRODUCE — quick pass-through since the repro test
   already exists, then Phase 1 INVESTIGATE with the scope set by the
   Adapt agent's `INVESTIGATION_SCOPE` directive).

4. If `.venv/bin/loop-state attempt` exits code 2 on the next call: revert,
   escalate to user.

### 4.3 Cleanup after revert

```bash
git branch | grep 'fix/' | xargs git branch -D 2>/dev/null
```

---

## PHASE 5 — REPORT & HANDBACK

Print a comprehensive report:

```
LOOP COMPLETE — Bug Fix Loop
============================
Bug:         <bug-id>
Attempts:    <N> / 2
Status:      <kept | reverted>

Investigation:
  Scope:     <NEIGHBORHOOD | SYSTEM>
  Pass 1 Accuracy: <accurate | partial | missed>
  Confidence: <HIGH | MEDIUM | LOW>

Reproduction:
  Test:      <test-file>::<test-name>
  Error:     <original error>

Fix:
  File/Line: <path>:<line>
  Hypothesis Used: <N> (<approach>)
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

| Type | Phase | Role | Tools | Parallel? |
|------|-------|------|-------|-----------|
| QA | 0 | Write a failing reproduction test | Bash, Write, Read | Yes (1-2 at once) |
| Investigator | 1 | Explore codebase, produce diagnostic brief with 2-3 fix hypotheses | Read, Bash, Glob | Yes (2 at once) |
| Refactoring | 2 | Apply surgical fix on a branch, guided by diagnostic brief | Bash, Write, Read | Yes (1-2 at once) |
| Auditor | 3 | Run bug test + regression suite | Bash, Read | Yes (one per fix) |
| Adapt | 4 | Analyze failure, propose new strategy, decide scope escalation | Read | No (sequential) |
