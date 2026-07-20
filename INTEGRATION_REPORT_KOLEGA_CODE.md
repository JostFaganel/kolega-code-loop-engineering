# Integration Report: Bug-Fix Loop as a Standard Kolega Code Feature

**Prepared for**: PR to `kolega-ai/kolega-code`
**Based on**: `kolega-code-loop-engineering` v3 — Investigation Phase with Scope Escalation
**Kolega Code version analyzed**: v0.21.0

---

## Executive Summary

Kolega Code already has the building blocks needed for a built-in bug-fix loop with broad investigation:

| Building block | Already exists in kolega-code | What's missing |
|---------------|-------------------------------|----------------|
| Read-only investigation sub-agent | `dispatch_investigation_agent` + `investigation.md.j2` prompt | Two-pass methodology (broad → narrow), structured output format |
| Coder sub-agent | `dispatch_coding_agent` + `coder_cli.md.j2` prompt | Bug-fix-specific instructions, hypothesis selection guidance |
| Parallel sub-agent dispatch | `dispatch_*_agent` with parallel fan-out | Coordination between investigation and fix phases |
| Gigacode orchestration | `parallel()`, `pipeline()`, `phase()`, `agent()` primitives | Pre-built "bug-fix" workflow template |
| Prompt overrides | `.kolega/prompts/` with Jinja2 templates | Bug-fix loop prompt override as a standard shipped template |
| Skills system | `.agents/skills/SKILL.md` with YAML frontmatter | Built-in `bug-fix-loop` skill |
| Goal loop | `/goal` with read-only verifier | Bug-fix mode for the goal loop with fix → verify → adapt logic |
| Agent types | Coder, Investigation, Browser, General, Planning | None — existing types are sufficient |

**The integration requires no new agent types, no new primitives, and no architectural changes.** The enhancement is purely in prompts, skills, and workflow patterns.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                   KOLEGA CODE ARCHITECTURE                   │
│                                                              │
│  ┌──────────┐   ┌──────────────┐   ┌───────────────────┐    │
│  │   TUI    │   │  CLI (ask,   │   │  Prompt Templates  │    │
│  │  (Textual)│   │  sessions,  │   │  (Jinja2 .j2)      │    │
│  │          │   │  doctor...)  │   │  per agent type    │    │
│  └────┬─────┘   └──────┬───────┘   └────────┬──────────┘    │
│       │                │                     │               │
│       └────────┬───────┘                     │               │
│                │                             │               │
│       ┌────────▼────────┐           ┌───────▼───────────┐   │
│       │  Slash Commands  │           │  Prompt Provider   │   │
│       │  /goal, /gigacode│           │  (agent type →     │   │
│       │  /plan, /settings│           │   template + vars) │   │
│       └────────┬─────────┘           └───────┬───────────┘   │
│                │                             │               │
│       ┌────────▼─────────────────────────────▼───────────┐   │
│       │                  AGENT LAYER                       │   │
│       │  ┌──────────┐ ┌──────────────┐ ┌──────────────┐  │   │
│       │  │  Coder   │ │ Investigation│ │   Planning   │  │   │
│       │  │ (edits)  │ │ (read-only)  │ │ (read-only)  │  │   │
│       │  └──────────┘ └──────────────┘ └──────────────┘  │   │
│       │  ┌──────────┐ ┌──────────────┐                   │   │
│       │  │ Browser  │ │   General    │                   │   │
│       │  │ (web)    │ │  (flexible)  │                   │   │
│       │  └──────────┘ └──────────────┘                   │   │
│       └──────────────────────┬───────────────────────────┘   │
│                              │                               │
│       ┌──────────────────────▼───────────────────────────┐   │
│       │            GIGACODE ORCHESTRATION                 │   │
│       │  agent() · parallel() · pipeline() · phase()      │   │
│       │  log() · args · budget                            │   │
│       └──────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────────┐│
│  │              EXTENSIBILITY POINTS                         ││
│  │  · .kolega/prompts/  (prompt overrides)                  ││
│  │  · .agents/skills/   (skill definitions)                 ││
│  │  · .agents/custom/   (custom agents)                     ││
│  │  · hooks/             (lifecycle hooks)                   ││
│  └──────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────┘
```

---

## Integration Approach: Three Layers

The bug-fix loop with investigation and scope escalation integrates at three layers, from deepest (most impactful) to shallowest (easiest to deploy):

| Layer | What changes | Impact | Effort |
|-------|-------------|--------|--------|
| **Layer 1**: Investigation prompt enhancement | Enhanced `investigation.md.j2` template | All investigation agents do broader exploration | Low |
| **Layer 2**: Built-in bug-fix skill | New `.agents/skills/bug-fix-loop/SKILL.md` | Coder agent knows the full bug-fix workflow | Low |
| **Layer 3**: Gigacode bug-fix workflow template | Standard workflow pattern for bug fixing | Automated orchestration of the full loop | Medium |

All three layers are independent — Layer 1 can ship alone, Layer 2 builds on it, Layer 3 builds on both.

---

## Layer 1: Enhanced Investigation Agent Prompt

### Current state

The investigation agent prompt (`investigation.md.j2`) is generic — it tells the agent to "explain a codebase" and "do not output code." It has no structured methodology for broad exploration or hypothesis generation.

### Proposed change

Enhance `kolega_code/agent/prompt_templates/system/agents/investigation.md.j2` to include a structured two-pass methodology:

**Pass 1 — Broad System Understanding** (before tracing the bug):
1. Architecture & conventions — module roles, design patterns, boundaries
2. Intended behavior — docs, specs, tests that define correct behavior
3. Recent changes — `git log`, `git blame` to find introduction points
4. Related features & analogues — similar modules, how they handle the same scenario

**Pass 2 — Multiple Fix Hypotheses** (after understanding the system):
1. Error path trace — follow execution from symptom to root cause
2. Unexpected root cause exploration — could it be config, state, a dependency?
3. Generate 2–3 distinct fix hypotheses — different approaches, trade-offs

**Scope awareness**: The investigation agent should scale its exploration depth based on the task complexity. For simple bugs, Pass 1 is lightweight. For complex/retry scenarios, Pass 1 expands to include global state, cross-cutting concerns, configuration surfaces, and test infrastructure audit.

### Files to create/modify

```
kolega_code/agent/prompt_templates/system/agents/investigation.md.j2  ← ENHANCE
```

**Key template variables to add**:
- `{{ investigation.scope }}` — "narrow" | "broad" | "system"
- `{{ investigation.bug_description }}` — optional, when investigating a bug
- `{{ investigation.repro_test }}` — optional, reproduction test details
- `{{ investigation.pass_2_enabled }}` — whether to generate fix hypotheses

### Simplified template sketch

```markdown
## Investigation Methodology

{% if investigation.bug_description %}
### Task: Investigate a Bug

**Bug**: {{ investigation.bug_description }}
{% if investigation.repro_test %}
**Reproduction**: {{ investigation.repro_test }}
{% endif %}
**Scope**: {{ investigation.scope | default("narrow") }}

#### Pass 1 — System Understanding (BROAD)
Before tracing the error, understand the system around the bug:
1. Read the affected module and adjacent modules — their roles, patterns, boundaries.
2. Find documentation, specs, and existing tests that define intended behavior.
3. Check recent changes: `git log` and `git blame` on affected files.
4. Find analogous modules — how do they handle the same scenario?

{% if investigation.scope == "broad" or investigation.scope == "system" %}
5. Audit global state, cross-cutting concerns (middleware, decorators).
6. Trace transitive dependencies — callers of callers, callees of callees.
7. Inspect configuration, environment variables, feature flags.
8. Check test infrastructure — could the test itself be wrong?
{% endif %}

#### Pass 2 — Fix Hypotheses (NARROW)
1. Trace the error path from symptom to root cause.
2. Explore unexpected root causes — config, state, dependencies.
3. Generate 2–3 DISTINCT fix hypotheses, each with: approach, rationale, risks, verification.

**Output format**: Return a structured diagnostic report with Pass 1 findings
and Pass 2 hypotheses.
{% endif %}
```

---

## Layer 2: Built-in Bug-Fix Loop Skill

### Current state

Kolega Code's skill system loads SKILL.md files from `.agents/skills/` (user and project level). Skills are PromptExtensions — they inject a skill catalog into the agent's prompt. Skills can also provide ToolExtensions (`list_skills`, `activate_skill`, `read_skill_resource`).

### Proposed change

Ship a built-in skill at `.agents/skills/bug-fix-loop/SKILL.md` that describes the full bug-fix workflow:

```yaml
---
name: Bug Fix Loop
description: |
  Five-phase autonomous bug-fixing workflow with broad investigation,
  multiple fix hypotheses, differential verification, and automatic
  scope escalation on retry. Phases: Reproduce → Investigate → Act →
  Check → Adapt → Report. Max 2 fix attempts.
trigger_keywords:
  - fix
  - bug
  - crash
  - error
  - broken
  - regression
  - not working
  - debug
  - repair
  - patch
  - resolve
  - incorrect
  - wrong
  - fails
---
```

The skill body would describe:
1. **Phase 0 — REPRODUCE**: Dispatch 1–2 investigation agents to write failing tests
2. **Phase 1 — INVESTIGATE**: Dispatch 2 investigation agents with broad scope to produce diagnostic briefs
3. **Phase 2 — ACT**: Dispatch 1–2 coding agents on separate branches with the diagnostic brief
4. **Phase 3 — CHECK**: Dispatch 1 auditor (investigation agent) per fix to run tests
5. **Phase 4 — ADAPT**: If all fixes fail, analyze and decide scope escalation
6. **Phase 5 — REPORT**: Print comprehensive report

### How the coder agent uses it

When a user says "fix the login crash," the coder agent:
1. Reads the skill catalog, finds the Bug Fix Loop skill
2. Activates the skill (reads SKILL.md)
3. Follows the phase instructions, dispatching sub-agents at each phase
4. Uses the enhanced investigation agent (Layer 1) for investigation phases
5. Decides scope escalation based on fix outcomes

### Files to create

```
kolega_code/agent/prompt_templates/extensions/bug_fix_loop_skill.md.j2  ← NEW
# Or as a static bundled skill shipped with the package
```

The skill should be distributed as a prompt extension (injecting skill catalog into the coder/planning agent prompt) rather than requiring users to install it separately. This makes it "built-in."

---

## Layer 3: Gigacode Bug-Fix Workflow Template

### Current state

Gigacode allows the agent to generate Python workflow scripts using `parallel()`, `pipeline()`, `phase()`, and `agent()` primitives. Workflows are generated dynamically — there are no pre-built templates.

### Proposed change

The coder agent, guided by the bug-fix skill (Layer 2), generates a Gigacode workflow script that automates the full loop. The workflow would look like:

```python
# Generated by the coder agent when Gigacode is enabled

# Phase 0: Reproduce
phase("🔍 REPRODUCE — Writing failing tests")
repro_results = await parallel([
    lambda: agent(
        "Write a minimal failing test for: ...",
        agent_type="investigation"
    ),
    lambda: agent(
        "Write an alternative failing test for: ...",
        agent_type="investigation"
    ),
])

# Phase 1: Investigate (NEIGHBORHOOD scope)
phase("🔬 INVESTIGATE — Broad exploration (NEIGHBORHOOD scope)")
diag_results = await parallel([
    lambda: agent(
        "Two-pass investigation. Bug: ... Test: ... Scope: NEIGHBORHOOD",
        agent_type="investigation",
        schema=DIAGNOSTIC_REPORT_SCHEMA
    ),
    lambda: agent(
        "Two-pass investigation. Bug: ... Test: ... Scope: NEIGHBORHOOD",
        agent_type="investigation",
        schema=DIAGNOSTIC_REPORT_SCHEMA
    ),
])

# Phase 2: Act (Surgical fixes)
phase("🔧 ACT — Applying fixes")
fix_results = await parallel([
    lambda: agent(
        f"Fix the bug. Diagnostic brief: {merged_diagnostics}. Branch: fix/v1-a",
        agent_type="coder",
    ),
    lambda: agent(
        f"Fix the bug. Diagnostic brief: {merged_diagnostics}. Branch: fix/v1-b",
        agent_type="coder",
    ),
])

# Phase 3: Check (Verification)
phase("✅ CHECK — Verifying fixes")
check_results = await parallel([
    lambda: agent(
        f"Verify fix on branch fix/v1-a. Run repro test + full suite.",
        agent_type="investigation",
        schema=CHECK_SCHEMA
    ) for fix in fix_results if fix is not None
])

# Phase 4: Adapt (if all failed)
if all_failed(check_results):
    phase("🔄 ADAPT — Analyzing failure")
    adapt_result = await agent(
        "Analyze why all fixes failed. Decide scope escalation.",
        agent_type="investigation",
        schema=ADAPT_SCHEMA
    )
    
    if adapt_result["scope"] == "SYSTEM":
        # Retry with SYSTEM scope
        phase("🔬 INVESTIGATE — Deep exploration (SYSTEM scope)")
        # ... broader investigation ...
        phase("🔧 ACT — Re-attempting fixes")
        # ... new fixes ...

# Phase 5: Report
phase("📊 REPORT — Loop complete")
```

### Structured schemas

The workflow uses JSON schemas for structured output:

```python
DIAGNOSTIC_REPORT_SCHEMA = {
    "type": "object",
    "properties": {
        "pass_1": {
            "type": "object",
            "properties": {
                "architecture": {"type": "string"},
                "intended_behavior": {"type": "string"},
                "recent_changes": {"type": "string"},
                "analogous_code": {"type": "string"},
                "scope": {"enum": ["NEIGHBORHOOD", "SYSTEM"]}
            }
        },
        "pass_2": {
            "type": "object",
            "properties": {
                "error_path": {"type": "string"},
                "unexpected_causes": {"type": "array", "items": {"type": "string"}},
                "hypotheses": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "approach": {"type": "string"},
                            "rationale": {"type": "string"},
                            "risks": {"type": "string"},
                            "verification": {"type": "string"},
                            "confidence": {"enum": ["HIGH", "MEDIUM", "LOW"]}
                        }
                    },
                    "minItems": 2,
                    "maxItems": 3
                }
            }
        },
        "overall_confidence": {"enum": ["HIGH", "MEDIUM", "LOW"]}
    }
}
```

### Files to create/modify

```
kolega_code/agent/prompt_templates/extensions/bug_fix_workflow_guide.md.j2  ← NEW
```

This would be a prompt extension that teaches the coder agent how to generate the Gigacode workflow script for bug fixing. It includes:
- The workflow pattern (phases, primitives)
- The structured schemas
- The scope escalation logic
- Error handling and edge cases

---

## Implementation Plan

### Phase 1: Ship Layer 1 (Investigation Prompt Enhancement)

**Files to modify**:
- `kolega_code/agent/prompt_templates/system/agents/investigation.md.j2`

**Changes**:
- Add optional `{% if investigation %}` block with two-pass methodology
- Add scope parameter: narrow → broad → system
- Add structured output guidance for diagnostic reports
- Add `{% if investigation.pass_2 %}` block for hypothesis generation

**Backward compatibility**: When `investigation` context is not provided (normal investigation tasks), the template renders identically to today. No behavior change for existing use cases.

**Tests**: Add unit tests for template rendering with and without `investigation` context.

### Phase 2: Ship Layer 2 (Built-in Bug-Fix Skill)

**Files to create/modify**:
- New skill definition (either as a prompt extension or bundled skill file)
- `kolega_code/agent/prompts.py` — register the skill as a default prompt extension

**Changes**:
- The bug-fix skill is injected into the coder agent's prompt as a `PromptExtension`
- The skill teaches the agent the REPRODUCE → INVESTIGATE → ACT → CHECK → ADAPT → REPORT workflow
- The agent dispatches sub-agents using existing `dispatch_*_agent` tools

**Backward compatibility**: The skill only activates when the user's request matches bug-fix keywords. Normal coding tasks are unaffected.

### Phase 3: Ship Layer 3 (Gigacode Workflow Template)

**Files to create/modify**:
- New prompt extension for Gigacode bug-fix workflow patterns
- Structured schemas for diagnostic reports, check results, adapt decisions
- `kolega_code/agent/prompt_templates/extensions/` — new extension templates

**Changes**:
- When Gigacode is enabled and the task is a bug fix, the coder agent generates a workflow script
- The workflow uses `parallel()`, `pipeline()`, `phase()`, and `agent()` primitives
- Structured schemas ensure reliable output from sub-agents
- Scope escalation is built into the workflow logic

**Backward compatibility**: Only activates when Gigacode is on AND the task is a bug fix.

### Phase 4 (Optional): Goal Loop Enhancement

**Files to modify**:
- `kolega_code/agent/goal.py` — add bug-fix mode
- `kolega_code/cli/slash_commands.py` — add `/fix-bug` command or extend `/goal`

**Changes**:
- A `/fix-bug` slash command that sets a bug-fix goal
- The goal loop runs the bug-fix workflow automatically
- Progress tracking through the goal verifier

---

## Comparison: Current State vs. Proposed State

| Aspect | Current kolega-code | After integration |
|--------|-------------------|-------------------|
| Bug investigation | Investigation agent explores codebase generically | Investigation agent follows structured two-pass methodology (broad → narrow) |
| Fix approach | Coder agent jumps to fix with limited context | Coder agent receives diagnostic brief with 2–3 fix hypotheses, chooses or combines |
| Retry behavior | Coder agent iterates on failing approach | After failure, investigation re-runs with broader scope (SYSTEM mode) |
| Orchestration | Manual sub-agent dispatch by coder agent | Optional Gigacode workflow automates the full loop |
| Skill availability | Users must install kolega-code-loop-engineering separately | Built-in skill, always available |
| State management | Users must install loop-state CLI | Optional — loop can work without state management for simple cases |

---

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| Enhanced investigation prompt increases token usage | Scope awareness (`narrow` default) keeps simple investigations lightweight |
| Bug-fix skill conflicts with user's custom prompts | Skill only activates on bug-fix keywords; user prompt overrides take precedence |
| Gigacode workflow is complex to generate reliably | Structured schemas ensure sub-agent output is parseable; fallback to manual dispatch if workflow fails |
| Scope escalation may not be needed for simple bugs | Escalation only triggers after a failed fix attempt; most bugs are fixed on attempt 1 |
| Changes to core prompt templates affect all users | Backward-compatible: `{% if %}` blocks ensure no behavior change without the context |

---

## Recommendations

1. **Ship Layer 1 first** — Enhanced investigation prompt. This is the smallest change with the broadest impact. Every investigation agent becomes more effective at exploring codebases broadly.

2. **Ship Layer 2 next** — Built-in bug-fix skill. This gives the coder agent a structured methodology for bug fixing without requiring Gigacode. Works in both Plan and Build modes.

3. **Ship Layer 3 as a follow-up** — Gigacode workflow template. This adds full automation for users who have Gigacode enabled. The workflow can handle the entire loop without the coder agent manually stepping through phases.

4. **Consider Layer 4 for v1.x** — Goal loop enhancement. A dedicated `/fix-bug` command would provide the best UX, but requires more design work on how the goal loop tracks progress through multiple phases.

---

## What kolega-code-loop-engineering Provides That kolega-code Doesn't (Yet)

| Feature | kolega-code-loop-engineering | kolega-code (after integration) |
|---------|------------------------------|-------------------------------|
| Work-log state (attempts, anti-patterns) | Built-in `loop-state` CLI | Not included (kolega-code has session persistence but not loop-specific state) |
| Git branch management | Automated branch naming and cleanup | Handled by coder agent (ad-hoc) |
| Anti-pattern memory | Cross-session anti-pattern recording | Could use kolega-code's memory system |
| Katra integration | Optional persistent memory | kolega-code has its own memory system |
| Deterministic revert | `loop-state revert` with git/rsync | Handled by coder agent (ad-hoc) |

The state management features of kolega-code-loop-engineering (attempt tracking, anti-patterns, deterministic revert) could remain as a companion package or be integrated into kolega-code's session/journal system in a future iteration.

---

## Summary

The bug-fix loop with broad investigation and scope escalation can be integrated into kolega-code as a standard feature through three incremental layers:

1. **Enhanced investigation prompt** — makes every investigation agent do broader exploration
2. **Built-in bug-fix skill** — teaches the coder agent the full workflow
3. **Gigacode workflow template** — automates the loop when Gigacode is enabled

All changes are backward-compatible, require no new agent types or primitives, and can ship incrementally. The total implementation effort is low (prompt templates + skill definitions) with high impact (eliminates target fixation for all kolega-code users).
