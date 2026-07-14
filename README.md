# Kolega Code Loop Engineering

Autonomous loop engineering for AI coding harnesses. Two tight feedback loops
with parallel sub-agents, deterministic state management, and strict
keep-or-revert rules.

**100% harness-agnostic.** Works with Kolega Code, Claude Code, Cursor,
Continue, or any harness that supports SKILL.md + Task tool.

---

## Quickstart

```bash
git clone https://github.com/kolegadev/kolega-code-loop-engineering.git
cd kolega-code-loop-engineering
pip install -e .
```

Then point your coding harness at this repo and say:

> "Follow SKILL.md. I need a calculator module: add, subtract, multiply, divide."

The agent will read the instructions, install the state manager, and execute
the autonomous loop with parallel Generator/Verifier sub-agents.

---

## How It Works

```
┌──────────────────────────────────────────────────────┐
│                   ORCHESTRATOR                        │
│              (reads SKILL.md, follows phases)          │
└──────┬──────────────┬──────────────┬─────────────────┘
       │              │              │
       ▼              ▼              ▼
┌─────────────┐ ┌───────────┐ ┌──────────────┐
│  Generator  │ │ Generator │ │   Verifier   │
│  (branch A) │ │ (branch B)│ │  (branch A)  │
└─────────────┘ └───────────┘ └──────────────┘
       │              │              │
       └──────────────┴──────┬───────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │   STATE MANAGER     │
                  │   (loop-state CLI)  │
                  │                     │
                  │  • work-log.json    │
                  │  • attempt limits   │
                  │  • git revert       │
                  │  • anti-patterns    │
                  └─────────────────────┘
```

### The Two Loops

| | New Code Loop | Bug Fix Loop |
|---|---|---|
| **Trigger** | New feature request | Bug report / issue |
| **Phases** | Goal → Generate → Verify → Select | Reproduce → Act → Check → Adapt |
| **Sub-agents** | Generator (2-3) + Verifier (1 per branch) | QA (1-2) + Refactoring (1-2) + Auditor (1 per fix) + Adapt |
| **Max attempts** | 3 | 2 |
| **Revert on** | All verifiers fail | Any fix causes regression |
| **Memory** | CONTRACT.md per task | Anti-pattern log per module |

---

## Configuration

The loops are configured via environment variables (see `templates/.env.example`):

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LOOP_TYPE` | Yes | — | `new-code` or `bug-fix` |
| `FEATURE_SPEC` | For new-code | — | What to build |
| `BUG_DESCRIPTION` | For bug-fix | — | What to fix |
| `LOOP_MAX_ATTEMPTS` | No | 3 (new) / 2 (fix) | Override attempt limit |
| `LOOP_WORK_LOG` | No | `work-log.json` | Path to state file |

---

## State Manager CLI

The `loop-state` command manages all loop state:

```
loop-state init <task-id> --loop-type <new-code|bug-fix>
loop-state attempt              # Increment counter (exits 2 if limit hit)
loop-state revert               # Print revert command (pipe to bash)
loop-state log --status kept --summary "..."
loop-state anti-pattern --pattern "..." --root-cause "..." --file "..." --line N --rule "..."
loop-state check-anti-patterns [--module "..."]
loop-state status [--json]
loop-state backup               # Snapshot working tree
```

---

## Integrations

### Katra (Optional Persistent Memory)

For cross-session memory (work log persistence, anti-pattern sharing across
projects, feature pattern recall), see `integrations/katra/README.md`.

Katra is **fully optional**. The core loops work standalone with local
`work-log.json` files.

---

## Extending — Adding a Third Loop

1. Create `skills/<your-loop>/SKILL.md` following the same phase structure
2. Create any templates in `skills/<your-loop>/`
3. Add a row to the routing table in the root `SKILL.md`

That's it — no code changes needed.

---

## Architecture Decisions

| Decision | Why |
|----------|-----|
| SKILL.md as orchestrator | Portable — works with any harness that supports SKILL.md + Task tool |
| Python CLI for state | Avoids JSON malformation by LLMs; provides exit codes for branching |
| click for CLI | Lightweight, standard, no exotic deps |
| Task tool for sub-agents | Native to Kolega Code / Claude Code; no custom orchestration needed |
| Git revert primary, rsync fallback | Git is ubiquitous; rsync handles non-Git projects |
| Anti-patterns in work-log.json | Self-contained; no external dependency |
| Katra in integrations/ | Core loops are zero-Katra; opt-in layer is fully separated |

---

## License

MIT — see [LICENSE](LICENSE).
