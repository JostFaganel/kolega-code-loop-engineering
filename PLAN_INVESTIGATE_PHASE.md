# Plan: Add Broad Investigation Phase to Bug Fix Loop

**Status**: PENDING REVIEW (v3 — scoped investigation with automatic escalation)
**Goal**: Eliminate "target fixation" by requiring broad system understanding
and multiple fix hypotheses before any code is changed, with automatic scope
escalation to full-system investigation when the first attempt fails.

---

## Problem Statement

The current bug-fix loop jumps from reproduction straight to surgical fixing:

```
REPRODUCE → ACT → CHECK → ADAPT → REPORT
```

Refactoring agents receive only: the reproduction test + anti-pattern history.
They lack broader codebase context — architecture, conventions, recent changes,
intended behavior, alternative explanations for the bug. This creates **target
fixation**: the agent sees the symptom, applies the narrowest fix that makes the
test pass, and either introduces a regression or fails to address the real
underlying cause.

A single "investigate then fix" pass is not enough — that just creates a
slightly wider version of the same fixation (the investigator's conclusion
becomes the new target). **True broad exploration means understanding the system
before hypothesizing about the bug, and generating multiple fix candidates
rather than converging on one.**

---

## Solution: Scoped Investigation with Automatic Escalation

```
Attempt 1 (NEIGHBORHOOD scope):
  REPRODUCE → INVESTIGATE → ACT → CHECK
                 ↑                    │
           Pass 1: BROAD         ┌────┘
           Pass 2: NARROW        │
                            FIX PASSES?
                            │YES       │NO
                            ▼          ▼
                          DONE      ADAPT
                                      │
                            ┌─────┐   │
                            │Scope│◄──┘
                            │ OK? │
                            └──┬──┘
                     NEIGHBORHOOD│SYSTEM
                            │      │
                            ▼      ▼
                    Retry with  Retry with
                    same scope  SYSTEM scope
                    different   (deep investigation:
                    hypothesis  global state, config,
                                cross-cutting, events,
                                transitive deps, side
                                effects, full git history)

Attempt 2 (escalated or not):
  REPRODUCE → INVESTIGATE → ACT → CHECK → REPORT
                 ↑
           Scope: NEIGHBORHOOD or SYSTEM
           (as directed by ADAPT)
```

### Design principles

| Principle | How it's enforced |
|-----------|-------------------|
| **System before symptom** | Pass 1 explores architecture, conventions, recent changes, and intended behavior — WITHOUT tracing the error path. The error path is only explored in Pass 2. |
| **Multiple hypotheses** | Investigators must produce 2–3 distinct fix hypotheses, not 1 conclusion. Refactoring agents choose or combine them. |
| **Alternatives, not answers** | The diagnostic brief presents hypotheses as options with trade-offs, not as a prescribed fix. Refactoring agents retain autonomy. |
| **Always-on, non-blocking** | Investigation always runs, never gates the loop, never consumes attempts. |
| **Read-only** | Investigators use Read, Bash, Glob only. No Write tool. |
| **Scope escalation** | Attempt 1 always uses NEIGHBORHOOD scope. On failure, ADAPT decides whether to escalate to SYSTEM scope for the retry. |

---

## New Phase Structure

| Phase | Name | Sub-agents | Parallel? | Consumes attempt? |
|-------|------|-----------|-----------|-------------------|
| 0 | REPRODUCE | QA (1–2) | Yes | No |
| **1** | **INVESTIGATE** | **Investigator (2)** | **Yes** | **No** |
| 2 | ACT | Refactoring (1–2) | Yes | **Yes** |
| 3 | CHECK | Auditor (1 per fix) | Yes | No |
| 4 | ADAPT | Adapt (1) | No | No |
| 5 | REPORT | — | — | — |

Always 2 Investigators (not 1–2) — diversity of perspective is critical when
exploring broadly.

---

## Scope Escalation: NEIGHBORHOOD → SYSTEM

The investigation has two scopes. The scope determines how broadly the
Investigators explore. It escalates automatically when the first fix attempt
fails and the Adapt agent determines the root cause may lie outside the
initial search area.

| Scope | When used | Search radius | Cost |
|-------|-----------|---------------|------|
| **NEIGHBORHOOD** | Attempt 1 (always) | Affected module + adjacent modules + direct dependencies + recent git history | Fast (10–30s of sub-agent time) |
| **SYSTEM** | Retry after ADAPT (conditional) | Full project: global state, cross-cutting concerns, transitive dependencies, configuration, external APIs, event flows, test infrastructure, full git history | Thorough (60–120s of sub-agent time) |

### How escalation works

```
Attempt 1:
  INVESTIGATE (scope: NEIGHBORHOOD) → ACT → CHECK
    │
    ├── FIX PASSES → done (most bugs caught here)
    │
    └── FIX FAILS → ADAPT analyzes
                       │
                       ├── Root cause looks local → scope stays NEIGHBORHOOD
                       │   (try different hypothesis from the existing set)
                       │
                       └── Root cause might be distant → scope = SYSTEM
                           (investigation goes full-system on retry)

Retry (Attempt 2):
  INVESTIGATE (scope: SYSTEM or NEIGHBORHOOD, as directed by ADAPT)
    → ACT (with expanded diagnostic brief) → CHECK → REPORT
```

### What SYSTEM scope adds

When scope is `SYSTEM`, the Investigation phase expands beyond the local
neighborhood. Investigators receive additional exploration mandates that
target the blind spots of the neighborhood scope:

| Exploration area | What it catches |
|-----------------|-----------------|
| **Global state audit** | Singletons, module-level variables, process-wide state that silently corrupts behavior |
| **Cross-cutting concerns** | Middleware, interceptors, decorators, hooks, AOP — code that executes around the buggy code without being in the call stack |
| **Transitive dependency graph** | Not just direct callers, but callers-of-callers and callees-of-callees — the full ripple radius |
| **Configuration surface** | All env vars, config files, feature flags, CLI args — any knob that could change behavior at runtime |
| **External dependency audit** | API clients, database connections, file I/O, message queues — side effects and failure modes at boundaries |
| **Event & message flow** | Pub/sub, event emitters, callbacks, websockets, polling loops — asynchronous behavior invisible in a synchronous trace |
| **Test infrastructure audit** | Is the test harness itself correct? Wrong mocks, stale fixtures, flaky setup, test ordering dependencies |
| **Full git history** | Not just recent commits — the entire history of the affected logic, including deleted code that may reveal original intent |
| **Side effect map** | What else happens during the error path? Logs, metrics, cache writes, state mutations — any of which could be the real culprit |

---

## Phase 1 — INVESTIGATE (Full Design)

### 1.1 Inputs

- Bug description (from env var, issue URL, or user prompt)
- Reproduction test path, name, and error message (from Phase 0)
- Anti-pattern history for the affected module
- **Investigation scope**: `NEIGHBORHOOD` (attempt 1, always) or `SYSTEM` (retry, set by ADAPT)
- **Adapt context** (only on retry): the Adapt agent's failure analysis and scope directive

### 1.2 Two-Pass Structure

Each Investigator runs **two sequential passes** internally. Pass 1 is purely
exploratory — no hypothesis formation. Pass 2 uses Pass 1's findings to
generate multiple hypotheses.

The **scope** determines how far Pass 1 reaches:

- **NEIGHBORHOOD**: affected module + adjacent modules + direct dependencies + recent git history
- **SYSTEM**: everything in NEIGHBORHOOD, PLUS global state, cross-cutting concerns, transitive dependencies, configuration, external APIs, event flows, test infrastructure, full git history, side effects

### 1.3 Investigator Prompt

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
WHY SCOPE WAS ESCALATED: <Adapt agent's reasoning for SYSTEM scope>

---

Your task: Conduct a TWO-PASS investigation. Pass 1 explores the system
broadly WITHOUT focusing on the bug. Pass 2 uses that understanding to
generate MULTIPLE fix hypotheses. Do NOT fix anything. Do NOT write code.

Your investigation SCOPE determines how far you reach. Follow the scope
exactly — do not go beyond it on NEIGHBORHOOD, do not stay narrow on SYSTEM.

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

<IF SCOPE IS "SYSTEM" — ALSO COMPLETE 1E–1J BELOW>

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

**Tools**: Read, Bash (grep/ripgrep/git/find), Glob — read-only. **No Write.**

### 1.4 Merge Results

Wait for both Investigators. Merge their reports:

- If both converge on the same hypothesis as highest confidence → present it
  as the leading hypothesis, but include the alternatives.
- If they disagree on the best approach → present both perspectives equally,
  note the disagreement — this is valuable information.
- If one Investigator found something the other missed (e.g., a recent commit
  that explains everything) → highlight that finding prominently.
- If both return LOW confidence → note it but proceed. Include everything.
- If one fails entirely → use the surviving report as-is.

**Key rule**: the merged diagnostic brief MUST retain all hypotheses from both
Investigators. Never discard alternatives. The Refactoring agent needs options.

### 1.5 Fallback

If both Investigators fail entirely (timeout, error, empty output), proceed to
ACT without the diagnostic brief. Investigation never blocks the loop.

### 1.6 Re-investigation on Retry

After ADAPT revert, Phase 0 re-verifies the repro test (quick pass-through).
Then Phase 1 INVESTIGATE runs fresh with the Adapt agent's analysis as
additional context. The Investigators see what failed before and why —
they can refine their hypotheses accordingly.

---

## Phase 2 — ACT (Modified from Old Phase 1)

The ACT phase structure is unchanged: 1–2 Refactoring agents on separate
branches. But the prompt is expanded to include the full diagnostic brief
with multiple hypotheses:

```
You are a Refactoring sub-agent in an autonomous bug-fix loop.

Your task: Fix the bug reproduced in <TEST_FILE> (<TEST_NAME>).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DIAGNOSTIC BRIEF (from investigation phase)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SYSTEM CONTEXT:
<Pass 1 findings: architecture, intended behavior, recent changes, analogues>

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
   rewrite whole modules.
3. Create a new git branch: fix/<task-id>-v<attempt>-<letter>
4. Apply the fix. Keep it surgical.
5. After fixing, check the RISK areas from each hypothesis you considered.
   Run any tests in those areas.
6. Run the reproduction test — it MUST now PASS.
7. Run the VERIFICATION checks from your chosen hypothesis.
8. AVOID KNOWN ANTI-PATTERNS:
   <paste output of loop-state check-anti-patterns>
9. If your fix doesn't work, try a DIFFERENT hypothesis rather than
   iterating on a failing approach.
10. Return:
    - BRANCH: <branch name>
    - FILES_CHANGED: <list>
    - FIX_LINE: <file:line>
    - HYPOTHESIS_USED: <which hypothesis you followed, or "combined" or "new">
    - REPRO_TEST_PASSES: true/false
    - RISK_AREA_CHECKS: <results>
    - VERIFICATION_CHECKS: <results>
    - SUMMARY: <1 sentence describing the fix and why this approach>
```

Key changes to the Refactoring prompt:
- **System context** block — architecture, conventions, recent changes
- **Multiple hypotheses** — agent chooses or combines, must justify choice
- **Unexpected root causes** — agent explicitly rules them out
- **Rule 1**: review all hypotheses, justify choice
- **Rule 9**: if fix fails, try a different hypothesis (don't bang head on wall)
- **Return field**: `HYPOTHESIS_USED` for traceability

---

## Phase 4 — ADAPT (Enhanced with Scope Escalation)

The Adapt agent now receives both the investigation reports AND the Auditor
failures. It evaluates whether the investigation was accurate and which
hypotheses should be pursued or abandoned. **Critically, it decides whether the
retry needs a broader investigation scope.**

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

Propose a refined approach:
- ANALYSIS: <why previous attempts failed, referencing investigation accuracy>
- PASS_1_ACCURACY: <was the system understanding correct? yes|partial|no>
- ABANDONED_HYPOTHESES: <which hypotheses are ruled out and why>
- RETAINED_HYPOTHESES: <which hypotheses are still viable>
- NEW_HYPOTHESIS: <if needed, a new approach not in the original set>
- NEW_STRATEGY: <concise direction for the retry>
- **INVESTIGATION_SCOPE: NEIGHBORHOOD | SYSTEM**
  Set to SYSTEM if the root cause may be outside the local neighborhood.
  Set to NEIGHBORHOOD if the existing investigation was sufficient and
  only the fix approach needs to change.
  DEFAULT: SYSTEM if previous scope was NEIGHBORHOOD and all fixes failed
  for reasons unrelated to the fix quality itself (e.g., "fix was correct
  but bug persisted").
```

### Scope escalation rules (for the orchestrator)

The orchestrator reads the Adapt agent's `INVESTIGATION_SCOPE` field:

| Previous scope | ADAPT says | Result |
|---------------|-----------|--------|
| NEIGHBORHOOD | NEIGHBORHOOD | Retry with same scope, different hypothesis |
| NEIGHBORHOOD | SYSTEM | Retry with SYSTEM scope — full deep investigation |
| SYSTEM | NEIGHBORHOOD | Retry with narrowed scope (unlikely but valid) |
| SYSTEM | SYSTEM | Retry with SYSTEM scope again (last attempt anyway) |

If the ADAPT agent does not specify a scope (malformed output), default to
SYSTEM on retry — safer to go broader than narrower when uncertain.

---

## Impact Assessment

### Before vs. After

| Aspect | Current (target fixation) | After (scoped + escalation) |
|--------|--------------------------|---------------------|
| Attempt 1 context | Reproduction test + anti-patterns only | Architecture, conventions, recent changes, intended behavior, analogous code, error path, 2–3 hypotheses |
| Attempt 2 context | Same as attempt 1 (blind retry) | Full-system deep investigation if ADAPT escalates: global state, cross-cutting concerns, transitive deps, config, external APIs, events, test infra, full git history, side effects |
| Fix approach | One narrow guess | Choose from 2–3 evidence-backed hypotheses per attempt |
| Root cause | Assumed to be at error site | Explicit exploration of unexpected root causes; on retry, scope-aware search for distant causes |
| Retry learning | Adapt sees only failure logs | Adapt sees investigation accuracy, can escalate scope or refine hypotheses |
| Regressions | Discovered late (Auditor Phase) | Risk areas flagged in hypotheses, pre-checked by Refactoring agent |
| Distant root causes | Never found (loop fails, escalates to user) | Caught on retry with SYSTEM scope — global state, config, async, side effects |

### Risk mitigation

| Concern | Mitigation |
|---------|-----------|
| Investigation takes too long | Pass 1 NEIGHBORHOOD is bounded (module + adjacent + git log). SYSTEM scope is only used on retry when it's justified — the time is spent where it matters. |
| Multiple hypotheses confuse rather than help | Hypotheses are ranked by confidence. Refactoring agent picks one and justifies. |
| Investigation might be wrong | Hypotheses are presented as options, not conclusions. Refactoring agent can override. ADAPT evaluates investigation accuracy and can escalate scope. |
| Always-on means always costs time | Trivial bugs → Neighborhood scope is fast (10–30s). System scope never triggers for trivial bugs because they're fixed on attempt 1. |
| SYSTEM scope could be overkill when not needed | ADAPT decides. The default heuristic ("escalate if all fixes failed for reasons unrelated to fix quality") is conservative — only escalates when the evidence points outside the neighborhood. |
| Scope escalation on last attempt might not help | True — but it's better than a blind retry. The user gets a richer failure report either way. |

---

## Files to Change

### 1. `skills/bug-fix-loop/SKILL.md` — Full rewrite

Insert Phase 1 INVESTIGATE with the two-pass design. Renumber phases 1–4 →
2–5. Expand ACT prompt with diagnostic brief and multiple hypotheses. Enhance
ADAPT prompt with investigation evaluation.

### 2. `skills/bug-fix-loop/POSTMORTEM.template.md` — Add investigation section

```markdown
## Investigation Findings
- System understanding (Pass 1) accuracy: <accurate | partial | missed>
- Hypothesis chosen: <which of the 2–3 hypotheses was used>
- Hypothesis accuracy: <did the chosen hypothesis match the actual fix>
- Unexpected root causes explored: <were any alternative causes valid>
```

### 3. `README.md` — Update phase table and sub-agent table

### 4. Root `SKILL.md` — No changes (delegates to skill file)

### 5. Python package — No changes (investigation is read-only, no new state)

---

## Open Questions

1. **Should Pass 1 include reading the ACTUAL test suite** (beyond the repro test)? Yes — included in "Intended Behavior" (1B). Understanding what the existing tests cover reveals design intent and edge cases the original author considered.

2. **What if both Investigators converge on a LOW-confidence hypothesis?** The loop proceeds. The Refactoring agent sees "all hypotheses are low confidence — be extra careful, check assumptions." This is still better than no investigation at all.

3. **Should Investigators also look at the test file itself?** Yes — the reproduction test might be wrong (testing the wrong thing, misunderstanding the API). Pass 1's "Intended Behavior" section and Pass 2's "Unexpected Root Cause" section both implicitly cover this.

---

**Updated plan ready for review. The key difference from v1: investigation now starts BROAD (system, not symptom), generates MULTIPLE hypotheses (not one conclusion), and presents them as OPTIONS (not prescriptions).**
