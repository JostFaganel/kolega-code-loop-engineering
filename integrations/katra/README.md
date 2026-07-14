# Katra Integration (Optional)

Adds persistent cross-session memory to the loop engineering system using
[Katra Agentic Memory](https://github.com/kolegadev/katra).

## What Katra Adds

| Feature | Without Katra | With Katra |
|---------|--------------|------------|
| Work log persistence | Local `work-log.json` per project | Synced to Katra, queryable across projects |
| Anti-pattern memory | Local to the project | Global — never repeat a mistake across repos |
| Feature patterns | Lost after loop completes | Searchable by future loops |
| Failure reports | Only in terminal output | Stored for retrospective analysis |

## Prerequisites

- Katra server running (local or remote)
- `KATRA_API_KEY` set in your environment
- Katra MCP server configured in your coding harness

## Setup

### 1. Configure the MCP server

Merge `katra-mcp.json` into your harness's MCP config. For Kolega Code,
this typically lives at `~/.config/kolega-code/mcp.json`:

```json
{
  "mcpServers": {
    "katra-agentic-memory": {
      "command": "npx",
      "args": ["-y", "@katra/mcp-server"],
      "env": {
        "KATRA_API_KEY": "${KATRA_API_KEY}",
        "KATRA_BASE_URL": "http://localhost:3112"
      }
    }
  }
}
```

### 2. Set environment variables

```bash
export KATRA_API_KEY=your-key-here
export KATRA_BASE_URL=http://localhost:3112
```

### 3. Verify connectivity

Restart your harness and confirm the Katra tools are available:

- `katra_store_memory`
- `katra_search_memory`
- `katra_get_working_memory`
- `katra_get_temporal_context`

### 4. Run a loop

The agent will automatically detect Katra tools and follow the
instructions in `integrations/katra/SKILL.md` to sync state after
each loop iteration.

## How the Agent Uses It

The root `SKILL.md` instructs the agent:

> If Katra MCP tools are available, read `integrations/katra/SKILL.md`
> and follow the post-loop sync instructions.

This means Katra is never referenced unless the tools are present —
zero overhead when running standalone.
