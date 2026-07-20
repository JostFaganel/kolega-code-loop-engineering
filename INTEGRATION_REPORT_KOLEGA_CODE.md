# Integration Report: Bug-Fix Loop as a Standard Kolega Code Feature

**Prepared for**: PR to `kolega-ai/kolega-code`
**Based on**: `kolega-code-loop-engineering` v3 — Investigation Phase with Scope Escalation
**Kolega Code version analyzed**: v0.21.0

---

## Executive Summary

Kolega Code already has the building blocks needed for a built-in bug-fix loop with broad investigation.

**The user types "fix the login crash" and the agent automatically runs the full REPRODUCE → INVESTIGATE → ACT → CHECK → ADAPT workflow.** No install, no slash command required. The coder agent detects bug-fix keywords, reads the built-in skill, dispatches investigation sub-agents to explore broadly, generates multiple fix hypotheses, and only then attempts a fix. If the first attempt fails, the investigation re-runs with broader SYSTEM scope.

This report covers: how the UX works, whether the `loop-state` CLI is still needed, and the technical integration layers.

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

## User Experience: How Users Trigger the Bug-Fix Loop

### Default behavior: keyword auto-detection (no slash command needed)

The most natural UX: the user just describes the bug and the agent handles it.

```
User:  "the login endpoint returns 500 when the password has special characters"
       "fix the payment rounding — it's off by one cent for amounts over $1000"
       "there's a crash in the CSV parser when the file is empty"

→ Coder agent reads its skill catalog
→ Sees the bug-fix-loop skill with trigger_keywords: [fix, bug, crash, error, broken,
  regression, not working, debug, repair, patch, resolve, incorrect, wrong, fails]
→ One or more keywords match → activates the skill
→ Follows REPRODUCE → INVESTIGATE → ACT → CHECK → ADAPT → REPORT workflow
→ Dispatches investigation sub-agents, coding sub-agents, auditor sub-agents
→ Returns comprehensive fix report
```

The user never types `/loop` or `/bug-fix`. They just describe the problem and the agent knows what to do. This is how skills currently work in kolega-code — the skill catalog is injected into the coder agent's prompt as a PromptExtension, and the agent decides when to use each skill.

### Explicit invocation: slash command (like `/loop` today)

For users who want to be explicit or when the task is ambiguous:

```
User:  /bug-fix the login endpoint returns 500

→ Invokes the skill explicitly via slash command
→ Same behavior as auto-detection, but forced
```

Skills in kolega-code automatically become slash commands: a skill at `.agents/skills/bug-fix/SKILL.md` is available as `/bug-fix <args>`. An auto-router skill (`/loop`) could also exist:

```
User:  /loop fix the login endpoint returns 500     → routes to bug-fix loop
       /loop build a calculator module               → routes to new-code loop
```

This mirrors the `commands/loop.md` auto-router from kolega-code-loop-engineering.

### Comparison to your plugin

| Your plugin today | Kolega Code equivalent |
|-------------------|----------------------|
| `/loop fix <bug>` | `/bug-fix <bug>` or just "fix the login crash" (auto-detect) |
| `/loop build <feature>` | `/new-code <feature>` or just "build a calculator" (auto-detect) |
| `commands/loop.md` (auto-router) | Skill with `trigger_keywords` — agent auto-detects and activates |
| `SKILL.md` (orchestrator follows phases) | Coder agent reads skill body, dispatches sub-agents at each phase |
| Install via `install.sh` | No install — built-in skill shipped with kolega-code |

### What the user sees during execution

As the agent runs the loop, the user sees progress in real time:

1. **Phase headers** in the transcript: "🔍 REPRODUCE", "🔬 INVESTIGATE", "🔧 ACT", "✅ CHECK"
2. **Sub-agent inspector** (`Ctrl+G`): each dispatched investigation, coding, and auditor agent visible with live trajectory
3. **Progress lines**: "Writing reproduction test...", "Exploring architecture...", "Generating fix hypotheses...", "Verifying fix on branch fix/v1-a..."
4. **Final report**: comprehensive markdown output with bug ID, investigation findings, fix details, regression results

---

## Do We Need the `loop-state` CLI?

**Short answer: No, not for the core functionality.** But it depends on how rigorous you want the loop enforcement to be.

### What the CLI provides and what kolega-code already has

| CLI feature | Needed in kolega-code? | kolega-code equivalent |
|-------------|----------------------|----------------------|
| `loop-state init <id>` | **No** | Task identity tracked in agent context or workflow variables |
| `loop-state attempt` (exit code 2 at limit) | **Partially** | Agent tracks attempts in its conversation context. Exit code enforcement not replicable, but agent can be instructed to stop after 2 failures. |
| `loop-state revert` | **No** | Coder agent runs `git checkout main && git branch -D fix/*` directly |
| `loop-state log --status kept` | **No** | Session journal persists all actions. `/diagnostics` shows session state. |
| `loop-state anti-pattern` | **No** | kolega-code's project memory (`/memory`) can store anti-patterns persistently |
| `loop-state check-anti-patterns` | **No** | Agent reads project memory before fixing |
| `loop-state status` | **No** | `/diagnostics` or agent's own context tracking |
| `loop-state backup` | **No** | Git operations handled by coder agent; session snapshots available |

### Three levels of rigor

| Level | What it uses | Attempt enforcement | Cross-session memory | Suitable for |
|-------|-------------|-------------------|---------------------|-------------|
| **Level 1: Agent context** | Agent tracks state in conversation | Agent instructed to stop after 2 failures (soft) | None | Most bugs, personal use |
| **Level 2: Project memory** | kolega-code's `/memory` for anti-patterns | Agent instructed + memory file tracks attempt count | Anti-patterns persist across sessions | Team use, recurring bugs |
| **Level 3: loop-state CLI** | External CLI for deterministic enforcement | Hard exit code at limit, cannot be bypassed | Full work-log with history | CI/CD, automated pipelines, compliance |

### Recommendation for v1

**Skip the CLI.** Ship Layers 1-3 (prompts, skill, Gigacode template) without requiring any additional tooling. The agent's context and kolega-code's built-in memory are sufficient for 95% of bug-fix scenarios. The CLI's main value — deterministic attempt enforcement — matters most in automated/CI contexts, which is a v2 concern.

If users need stronger enforcement later, `kolega-code-loop-engineering` can be installed as a companion package that provides the CLI. The skill can detect whether `loop-state` is available and use it if present, falling back to agent-context tracking otherwise.

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

### Phase 4: Ship Layer 4 (Loop State — Deterministic Enforcement)

> **This is the CLI integration. It ports `loop-state` into kolega-code as native agent tools with hard enforcement.**

#### 4.1 Why deterministic enforcement matters

The skill (Layer 2) and Gigacode workflow (Layer 3) both rely on the agent *choosing* to stop after 2 attempts. A sufficiently determined agent can ignore this and keep trying forever. The `loop-state` CLI solves this with `exit code 2` — a hard signal that the agent runtime cannot ignore.

In kolega-code, the equivalent is a **tool that returns a structured signal** the agent is instructed to obey. But the real power is making it a **runtime check**, not just a suggestion.

#### 4.2 Architecture: LoopState as an agent tool + runtime guard

```
┌──────────────────────────────────────────────────────┐
│                  CODER AGENT                          │
│                                                      │
│  "I'm running the bug-fix loop. Before I fix,        │
│   I call loop_attempt(). If it says 'exceeded',      │
│   I MUST stop."                                      │
│                                                      │
│  Tools available:                                     │
│  ┌──────────────────────────────────────────────┐    │
│  │ loop_init(task_id, loop_type, max_attempts)  │    │
│  │ loop_attempt() → {attempt, max, exceeded}    │    │
│  │ loop_revert() → shell command string         │    │
│  │ loop_log(status, summary, phase)             │    │
│  │ loop_anti_pattern(pattern, cause, file, ...) │    │
│  │ loop_check_anti_patterns(module) → [...]     │    │
│  │ loop_status() → full work-log dict           │    │
│  │ loop_backup() → snapshot path                │    │
│  └──────────────────────────────────────────────┘    │
│                                                      │
│  Runtime guard:                                       │
│  ┌──────────────────────────────────────────────┐    │
│  │ Before each agent turn, check work-log.json   │    │
│  │ If attempts_made > max_attempts:              │    │
│  │   → Force agent to stop                       │    │
│  │   → Print "Loop limit exceeded" report        │    │
│  │   → Return control to user                    │    │
│  └──────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────┘
```

#### 4.3 Implementation: New Python module `kolega_code/loop/`

**Files to create:**

```
kolega_code/loop/
├── __init__.py          # Public API
├── state.py             # WorkLog class (ported from kolega-code-loop-engineering)
├── tools.py             # LoopStateTools — agent-callable tools
├── guard.py             # Runtime guard — checks limits before agent turns
└── schemas.py           # Work-log JSON schema
```

**`state.py` — WorkLog class (adapted from existing `state_manager.py`)**

Key adaptations for kolega-code:

| Original | Adapted for kolega-code |
|----------|------------------------|
| `path = "work-log.json"` | `path = state_dir / "projects" / project_hash / "loops" / task_id / "work-log.json"` |
| Standalone file | Uses `kolega_code.local_state` for state directory |
| `click` CLI commands | Methods called directly by tool collection |
| `print()` to stderr | Uses kolega-code's logging/event system |
| `exit(2)` for limit | Raises `LoopLimitExceeded` exception caught by guard |

```python
# kolega_code/loop/state.py (sketch)

from pathlib import Path
from kolega_code.local_state import get_state_dir

class LoopLimitExceeded(Exception):
    """Raised when attempt counter exceeds max_attempts."""
    def __init__(self, attempts_made: int, max_attempts: int):
        self.attempts_made = attempts_made
        self.max_attempts = max_attempts

class WorkLog:
    """Persistent loop state in kolega-code's state directory."""
    
    @classmethod
    def for_task(cls, project_path: str, task_id: str) -> "WorkLog":
        project_hash = _hash_path(project_path)
        path = get_state_dir() / "projects" / project_hash / "loops" / task_id / "work-log.json"
        return cls(path)
    
    def inc_attempt(self) -> int:
        """Increment and save. Raises LoopLimitExceeded if over limit."""
        self._data["attempts_made"] += 1
        self.save()
        if self._data["attempts_made"] > self._data["max_attempts"]:
            raise LoopLimitExceeded(
                self._data["attempts_made"], 
                self._data["max_attempts"]
            )
        return self._data["attempts_made"]
    
    # ... init, log, anti_pattern, revert, backup, status methods ...
```

**`tools.py` — Agent-callable loop state tools**

```python
# kolega_code/loop/tools.py (sketch)

from kolega_code.agent.tool_backend import ToolRegistry
from kolega_code.loop.state import WorkLog, LoopLimitExceeded

class LoopStateTools:
    """Tools the agent calls to manage deterministic loop state."""
    
    def __init__(self, project_path: str, task_id: str):
        self._worklog = WorkLog.for_task(project_path, task_id)
    
    def loop_init(
        self, 
        task_id: str, 
        loop_type: str,  # "bug-fix" | "new-code"
        max_attempts: int = 2
    ) -> dict:
        """Initialize a new loop work-log.
        
        Returns: {"task_id": ..., "loop_type": ..., "max_attempts": ...}
        """
        ...
    
    def loop_attempt(self) -> dict:
        """Increment the attempt counter.
        
        Returns: {"attempt": N, "max": M, "exceeded": false}
        If limit exceeded, returns {"exceeded": true} AND raises
        LoopLimitExceeded which the runtime guard catches.
        """
        try:
            n = self._worklog.inc_attempt()
            return {"attempt": n, "max": self._worklog.max_attempts, "exceeded": False}
        except LoopLimitExceeded as e:
            return {"attempt": e.attempts_made, "max": e.max_attempts, "exceeded": True}
    
    def loop_revert(self) -> dict:
        """Return the shell command to revert to last known-good state."""
        ...
    
    def loop_log(self, status: str, summary: str, phase: str = "") -> dict:
        """Record an attempt in the history."""
        ...
    
    def loop_anti_pattern(
        self, pattern: str, root_cause: str, 
        file: str, line: int, prevention_rule: str
    ) -> dict:
        """Record an anti-pattern for future loops."""
        ...
    
    def loop_check_anti_patterns(self, module: str = "") -> dict:
        """Query past anti-patterns, optionally filtered by module."""
        ...
    
    def loop_status(self) -> dict:
        """Return the full work-log as a dict for reporting."""
        ...
    
    def loop_backup(self) -> dict:
        """Snapshot the current working tree."""
        ...
```

**`guard.py` — Runtime enforcement**

This is the key innovation beyond what `loop-state` CLI provides. Instead of relying on the agent to check `loop_attempt()` results, a **runtime guard** checks before every agent turn:

```python
# kolega_code/loop/guard.py (sketch)

from kolega_code.loop.state import WorkLog

async def loop_limit_guard(agent_context) -> bool:
    """Called before each agent turn. Returns False to block the turn."""
    task_id = agent_context.get("loop_task_id")
    if not task_id:
        return True  # No active loop, allow
    
    wl = WorkLog.for_task(agent_context["project_path"], task_id)
    
    if wl.attempts_made > wl.max_attempts:
        # Force stop — agent cannot proceed
        await agent_context.send_message(
            f"⛔ Loop limit exceeded: {wl.attempts_made}/{wl.max_attempts} attempts. "
            f"Reverting and handing back to user."
        )
        # Trigger revert
        revert_cmd = wl.revert()
        if revert_cmd:
            await agent_context.exec_command(revert_cmd)
        return False  # Block the turn
    
    return True  # Allow the turn
```

This guard would be registered as a lifecycle hook in kolega-code's agent runtime, ensuring the agent physically cannot exceed the attempt limit — even if it ignores the `loop_attempt()` return value.

#### 4.4 Integration points

| Integration point | What changes |
|------------------|-------------|
| `kolega_code/agent/baseagent.py` | Register `LoopStateTools` in the coder agent's tool collection when a bug-fix loop is active |
| `kolega_code/agent/conversation.py` | Call `loop_limit_guard` before each agent turn |
| `kolega_code/loop/` | New module with state, tools, guard, schemas |
| `kolega_code/agent/prompts.py` | Inject loop state awareness into the bug-fix skill prompt |
| `kolega_code/local_state.py` | Add loop state directory to state directory layout |

#### 4.5 How the agent uses these tools

The bug-fix skill instructs the coder agent:

```
## Loop State Management

At the start of each bug-fix loop, call loop_init():
  loop_init("div-by-zero", "bug-fix", max_attempts=2)

Before any fix attempt (Phase 2 — ACT), call loop_attempt():
  result = loop_attempt()
  # If result.exceeded is True, you MUST stop and hand back.
  # The runtime will also enforce this automatically.

After a successful fix, call loop_log():
  loop_log("kept", "Fixed division by zero in calculate_tax()", phase="act")

After recording a lesson, call loop_anti_pattern():
  loop_anti_pattern(
    "no-zero-guard", "calculate_tax() did not check for zero divisor",
    file="src/tax.py", line=42, 
    prevention_rule="Always validate divisor before division"
  )

Before reverting, call loop_revert() and pipe to bash.

At the end of the loop, call loop_status() to include the full state
in the handback report.
```

#### 4.6 Files summary for Layer 4

| File | Purpose |
|------|---------|
| `kolega_code/loop/__init__.py` | Public API exports |
| `kolega_code/loop/state.py` | `WorkLog` class — JSON persistence, attempt limits, revert, anti-patterns |
| `kolega_code/loop/tools.py` | `LoopStateTools` — agent-callable methods auto-discovered as tools |
| `kolega_code/loop/guard.py` | `loop_limit_guard` — runtime check before agent turns |
| `kolega_code/loop/schemas.py` | JSON schema for work-log.json v1.0 |
| Tests: `tests/loop/` | Unit tests for WorkLog, tools, guard |

---

## Comparison: Current State vs. Proposed State

| Aspect | Current kolega-code | After all 4 layers |
|--------|-------------------|-------------------|
| Bug investigation | Investigation agent explores codebase generically | Investigation agent follows structured two-pass methodology (broad → narrow) |
| Fix approach | Coder agent jumps to fix with limited context | Coder agent receives diagnostic brief with 2–3 fix hypotheses, chooses or combines |
| Retry behavior | Coder agent iterates on failing approach | After failure, investigation re-runs with broader scope (SYSTEM mode) |
| Orchestration | Manual sub-agent dispatch by coder agent | Optional Gigacode workflow automates the full loop |
| Skill availability | Users must install kolega-code-loop-engineering separately | Built-in skill, always available |
| Attempt enforcement | Agent's discretion (can ignore limits) | **Hard enforcement**: runtime guard blocks agent after 2 failed attempts |
| Anti-pattern memory | None for bug-fix loops | Cross-session anti-pattern recording and querying per module |
| Deterministic revert | Agent runs git commands ad-hoc | `loop_revert()` returns exact revert command with git + rsync fallback |
| Loop state visibility | None | `loop_status()` returns full work-log for debugging and reporting |

---

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| Enhanced investigation prompt increases token usage | Scope awareness (`narrow` default) keeps simple investigations lightweight |
| Bug-fix skill conflicts with user's custom prompts | Skill only activates on bug-fix keywords; user prompt overrides take precedence |
| Gigacode workflow is complex to generate reliably | Structured schemas ensure sub-agent output is parseable; fallback to manual dispatch if workflow fails |
| Scope escalation may not be needed for simple bugs | Escalation only triggers after a failed fix attempt; most bugs are fixed on attempt 1 |
| Changes to core prompt templates affect all users | Backward-compatible: `{% if %}` blocks ensure no behavior change without the context |
| Loop state guard could block legitimate retries | Guard only activates for active bug-fix loops; normal coding sessions unaffected |
| Work-log.json could corrupt | Atomic saves (temp file + os.replace), corruption recovery from template, same as proven state_manager.py |
| Loop state tools add surface area | All tools are read-only or write to a single JSON file; no new external dependencies |

---

## Recommendations

1. **Ship Layer 1 first** — Enhanced investigation prompt. Smallest change, broadest impact. Every investigation agent becomes more effective.

2. **Ship Layer 2 next** — Built-in bug-fix skill. Teaches the coder agent the full workflow. Works in Plan and Build modes. No code changes.

3. **Ship Layer 3 as a follow-up** — Gigacode workflow template. Full automation for Gigacode users. Structured schemas for reliable sub-agent output.

4. **Ship Layer 4 with Layer 2** — Loop state tools + runtime guard. The agent tools (`loop_init`, `loop_attempt`, etc.) ship alongside the skill since the skill references them. The runtime guard can ship as a follow-up if the team wants to iterate on the enforcement mechanism separately.

---

## What kolega-code-loop-engineering Provides That kolega-code Integrates

| Feature | kolega-code-loop-engineering (plugin) | kolega-code (after Layer 4) |
|---------|--------------------------------------|---------------------------|
| Work-log state (attempts, anti-patterns) | `loop-state` CLI (separate binary) | `LoopStateTools` — native agent tools + runtime guard |
| Git branch management | Automated via CLI commands | Handled by coder agent following skill instructions |
| Anti-pattern memory | work-log.json with per-module queries | Same WorkLog class, stored in kolega-code state directory |
| Deterministic attempt enforcement | Exit code 2 from CLI | `LoopLimitExceeded` exception + runtime guard |
| Deterministic revert | `loop-state revert \| bash` | `loop_revert()` tool returns the command |
| Katra integration | Optional MCP integration | Unchanged — kolega-code has its own memory system |

---

## Summary

The bug-fix loop with broad investigation, scope escalation, and deterministic enforcement can be integrated into kolega-code as a standard feature through four incremental layers:

| Layer | What it does | Effort | Impact |
|-------|-------------|--------|--------|
| 1. Enhanced investigation prompt | Two-pass methodology in `investigation.md.j2` | Low | Every investigation agent does broader exploration |
| 2. Built-in bug-fix skill | `bug-fix-loop` skill with REPRODUCE→INVESTIGATE→ACT→CHECK→ADAPT workflow | Low | Agent knows the full methodology |
| 3. Gigacode workflow template | Automated workflow with structured schemas | Medium | Full automation when Gigacode is on |
| 4. Loop state tools + guard | `LoopStateTools` + runtime enforcement | Medium | Hard attempt limits, anti-pattern memory, deterministic revert |

**All layers are backward-compatible, require no new agent types or primitives, and can ship incrementally.** Layers 1-2 are prompt/skill changes only. Layers 3-4 add Python modules but don't touch the agent runtime core (except the guard hook).
