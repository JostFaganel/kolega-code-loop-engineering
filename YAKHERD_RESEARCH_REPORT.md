# Research Report: Yakherd + Kolega Code + Loop Engineering

**Repo analyzed**: https://github.com/gigajeff/Yakherd
**Date**: 2026-07-20

---

## What Yakherd Is

Yakherd is a **governance harness for agentic coding projects**. It installs a
repository-centered Single Source of Truth (SSOT) that gives agents strict
operating rules before any product code is written. Its core claim is
**recoverability**: a fresh agent with no chat history can open the repo,
reconstruct the entire project state from files alone, run checks, and issue
an independent review.

### Five Governance Roles

| Role | What it does | Loop equivalent |
|------|-------------|-----------------|
| **Architecture** | Reads all evidence, produces bounded plan with invariants, tradeoffs, stop gates. Never writes code. | **Investigator** (Phase 1) |
| **Implementation** | Executes within approved scope, writes evidence. | **Coder/Refactoring** agent (Phase 2) |
| **Red Team** | Independent review with severity-rated findings (P0–P3), exact file:line evidence. Never repairs. | **Auditor** (Phase 3) |
| **Temporary Branch** | Isolates exploratory work from main implementation. | Git branches in ACT phase |
| **Governor** | Audits state drift with delta-only reporting. | **Runtime guard** (Layer 4) |

### Governance Files

| File | Purpose | Loop equivalent |
|------|---------|-----------------|
| `AGENTS.md` | Authoritative operating rules | Bug-fix + new-code loop extensions |
| `SSOT.md` | Authority map — one file owns each fact | `WorkLog` schema |
| `DECISIONS.md` | Durable decision record with predecessor/successor tracking | Anti-pattern memory + history |
| `STATUS.md` | Bounded current-state index (strict length limits) | `loop_state_status()` |
| `CLAUDE.md` | One-line adapter importing AGENTS.md | PromptExtension registration |

---

## How Yakherd Complements Kolega Code

### 1. SSOT for Loop State (replace work-log.json)

Yakherd's SSOT principle — "one durable fact has one owner, summaries link but
never mirror mutable detail" — would make loop state **human-readable and
agent-recoverable**. Instead of a JSON file only the loop tools can parse,
DECISIONS.md could track why each fix was attempted, why it succeeded or
failed, and what anti-pattern was recorded. A fresh agent could read it without
any tooling.

**Current**: `~/.local/state/kolega-code/projects/<hash>/loops/<id>/work-log.json`
**With Yakherd**: `docs/loop/decisions/<bug-id>.md` — a markdown file any agent or human can read.

### 2. Role Separation Maps Perfectly to Loop Phases

Yakherd's role model is a **pre-built governance framework** that validates the
loop's sub-agent model:

```
Yakherd role        →  Loop sub-agent         →  Loop phase
─────────────────────────────────────────────────────────────
Architecture        →  Investigation agent     →  Phase 1 (INVESTIGATE)
Implementation      →  Coder/Refactoring agent →  Phase 2 (ACT)
Red Team            →  Auditor agent           →  Phase 3 (CHECK)
Governor            →  Runtime guard           →  Layer 4 enforcement
Temporary Branch    →  Git branch isolation    →  ACT phase branches
```

This isn't just similar — it's the **same architecture discovered
independently**. Yakherd validates that the loop's phase structure is a
general-purpose governance pattern, not just a bug-fix trick.

### 3. Recoverability = Loop Resilience

Yakherd's strongest feature is cold resume: "a new agent should be able to
open the generated repository with no implementation chat, reconstruct the
project's state from its files, run the required checks, and issue an
independent review."

This is exactly what the loop needs when:
- A session is interrupted mid-loop
- A new agent needs to pick up where the previous one left off
- The runtime guard triggers a revert and a fresh agent must understand what happened

**Current loop weakness**: If the agent crashes mid-loop, the next agent has
no context except the work-log.json. With Yakherd-style governance files, the
next agent could read DECISIONS.md ("what was tried"), STATUS.md ("where are
we in the loop"), and SSOT.md ("who owns what right now") and continue.

### 4. Decision Tracking Enhances Anti-Pattern Memory

Yakherd's DECISIONS.md has fields that directly improve the loop's
anti-pattern system:

| DECISIONS.md field | Maps to loop feature |
|-------------------|---------------------|
| Date | When the fix was applied |
| Status | kept / reverted |
| Current owner | Which file was changed |
| Supersedes | Previous fix attempt |
| Retained boundary | Risk areas that were checked |
| Decision | Root cause + fix summary |
| Evidence | Test results, coverage |

This is a richer, more auditable format than the current JSON history array.

### 5. Governor = Runtime Guard with More Teeth

Yakherd's Governor role audits state drift with delta-only reporting. The
current runtime guard just checks attempt counts. A Governor-style guard could:

- **Delta-only checks**: What files changed since the last green commit?
- **Owner violations**: Did a fix modify files it wasn't authorized to touch?
- **Status drift**: Is STATUS.md consistent with the actual repo state?
- **Evidence gaps**: Do all claimed fixes have corresponding test results?

---

## How Loop Engineering Principles Enhance Yakherd

### 1. Broad Investigation Before Architecture Decisions

Yakherd's Architecture role makes decisions based on reading existing files —
but it doesn't have a **two-pass methodology** (broad → narrow). The loop's
investigation phase would make Yakherd's Architecture more effective:

```
Yakherd Architecture (current):     Read files → decide → plan
With loop investigation:            Broad exploration → narrow analysis → multiple hypotheses → decide → plan
```

### 2. Multiple Hypotheses Before Selection

Yakherd's Architecture produces **one** plan. The loop's investigation produces
**2-3 fix hypotheses**. This pattern could improve Yakherd: instead of one
architecture plan, generate 2-3 plans with trade-offs, then let the Red Team
review all of them before Implementation picks one.

### 3. Deterministic Enforcement

Yakherd's roles are **voluntary** — the agent chooses to follow them. The
loop's runtime guard provides **hard enforcement** — the agent physically cannot
exceed attempt limits. Adding this to Yakherd would mean:

- Architecture cannot produce a second plan without explicit authorization
- Implementation cannot write to files outside the approved scope
- Red Team cannot skip findings

### 4. Scope Escalation

The loop's NEIGHBORHOOD → SYSTEM scope escalation is a governance pattern
Yakherd doesn't have. When Architecture's first plan fails, it should
automatically escalate to broader analysis — exactly like the loop does.

---

## Concrete Integration Ideas

### Idea A: Yakherd as a Project-Level Governance Layer for Loop State

```
my-project/
├── AGENTS.md              ← Yakherd governance rules + loop extensions
├── SSOT.md                ← Authority map (who owns what)
├── DECISIONS.md           ← Decision log (why fixes were made)
├── STATUS.md              ← Current project state + active loop phase
├── docs/
│   ├── loop/
│   │   └── anti-patterns/ ← Per-module anti-pattern records
│   ├── plans/             ← Architecture plans (investigation reports)
│   ├── reviews/           ← Red Team reviews (auditor reports)
│   └── run_records/       ← Loop execution records
└── src/
```

When the bug-fix loop runs, it:
1. Reads STATUS.md to see if a loop is already active
2. Reads DECISIONS.md for past anti-patterns
3. Writes investigation reports to `docs/plans/`
4. Writes auditor reports to `docs/reviews/`
5. Updates STATUS.md with current phase
6. Records decisions in DECISIONS.md

### Idea B: Loop Roles as Yakherd Role Extensions

Add two new roles to Yakherd's five:

| New Role | What it does |
|----------|-------------|
| **Investigator** | Two-pass exploration before Architecture. Produces diagnostic brief with multiple hypotheses. Read-only. |
| **Scope Escalator** | After Implementation fails, decides whether to retry with NEIGHBORHOOD or SYSTEM scope. Writes scope decision to DECISIONS.md. |

### Idea C: Yakherd-Style Recovery for Loop Sessions

Add a `bootstrap_cold_resume_loop.md` prompt that teaches a fresh agent how to
reconstruct loop state from governance files — no work-log.json needed:

1. Read STATUS.md → what phase is the loop in?
2. Read DECISIONS.md → what fixes were tried?
3. Read SSOT.md → what files are in play?
4. Read review records → what did the auditor find?
5. Resume from the appropriate phase

---

## Risk and Limitations

| Concern | Assessment |
|---------|-----------|
| Yakherd adds governance overhead | True — but only for projects that need it. The loop already has this overhead (SKILL.md readings, phase requirements). Yakherd just makes it durable. |
| Two governance systems might conflict | Yakherd's AGENTS.md and the loop extensions would need careful merging. SSOT.md principle says AGENTS.md is the authority — loop extensions become sections within it. |
| Yakherd targets new projects | Yes — its "fresh mode" assumes an empty repo. Retrofitting onto existing projects requires a separately reviewed JSON plan. The loop would need a retrofit pathway. |
| File-based state vs. JSON state | Human-readable markdown is great for agents and humans, but harder to parse programmatically. The loop guard needs structured data. Solution: keep WorkLog for programmatic enforcement, use Yakherd files for agent context. |

---

## Recommendations

1. **Adopt Yakherd's SSOT principle for loop state files** — move anti-pattern
   records and decision history from work-log.json into human-readable markdown
   files that follow SSOT.md authority rules.

2. **Map loop phases to Yakherd roles explicitly** — the alignment is too
   strong to ignore. Document it as "The Loop Governance Model" showing how
   Investigation = Architecture, Act = Implementation, Check = Red Team.

3. **Add cold-resume capability to the loop** — inspired by Yakherd's
   bootstrap_cold_resume_review.md, create a loop resume prompt that lets a
   fresh agent reconstruct loop state from governance files.

4. **Consider Yakherd as an optional governance layer** — users who already
   use Yakherd get loop state management "for free" through its file structure.
   Users who don't use Yakherd continue with the current WorkLog + tools
   approach. Both paths are valid.

5. **Investigate the Governor role for enhanced runtime guard** — Yakherd's
   delta-only auditing could replace or augment the simple attempt-count check
   with file-level scope enforcement and evidence verification.
