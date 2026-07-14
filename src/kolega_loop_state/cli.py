"""CLI for loop-state — manage work-log.json from the command line."""

import json
import os
import sys
from typing import Optional

import click

from kolega_loop_state.state_manager import AttemptLimitExceeded, WorkLog

WORK_LOG_PATH = os.environ.get("LOOP_WORK_LOG", "work-log.json")


def _load() -> WorkLog:
    """Load work-log, creating it if it does not exist."""
    return WorkLog.load(WORK_LOG_PATH)


# ---------------------------------------------------------------------------
# Main group
# ---------------------------------------------------------------------------

@click.group()
def main() -> None:
    """Manage autonomous loop state (work-log.json)."""


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------

@main.command()
@click.argument("task-id")
@click.option(
    "--loop-type",
    type=click.Choice(["new-code", "bug-fix"]),
    required=True,
    help="Which loop to run.",
)
def init(task_id: str, loop_type: str) -> None:
    """Create work-log.json for a new task."""
    max_env = os.environ.get("LOOP_MAX_ATTEMPTS")
    max_attempts = 3 if loop_type == "new-code" else 2
    if max_env is not None:
        try:
            max_attempts = int(max_env)
        except ValueError:
            click.echo(
                f"WARNING: LOOP_MAX_ATTEMPTS='{max_env}' is not an integer. "
                f"Using default {max_attempts}.",
                err=True,
            )

    wl = _load()
    wl._data["task_id"] = task_id
    wl._data["loop_type"] = loop_type
    wl._data["max_attempts"] = max_attempts
    wl._data["attempts_made"] = 0
    wl._data["history"] = []
    wl._data["anti_patterns"] = []
    wl._data["last_green_commit"] = None
    wl._data["last_green_backup"] = None
    wl.save()

    click.echo(
        f"init: task_id={task_id}  loop_type={loop_type}  "
        f"max_attempts={max_attempts}"
    )


# ---------------------------------------------------------------------------
# attempt
# ---------------------------------------------------------------------------

@main.command()
def attempt() -> None:
    """Increment attempt counter. Exits 2 if limit exceeded."""
    wl = _load()
    try:
        n = wl.inc_attempt()
        click.echo(
            f"Attempt {n} of {wl.max_attempts} "
            f"(task: {wl._data.get('task_id')})"
        )
    except AttemptLimitExceeded as exc:
        click.echo(
            f"ABORT: Attempt limit exceeded ({exc.attempts_made}/"
            f"{exc.max_attempts}). Escalate to operator.",
            err=True,
        )
        sys.exit(2)


# ---------------------------------------------------------------------------
# revert
# ---------------------------------------------------------------------------

@main.command()
def revert() -> None:
    """Print the revert command to stdout."""
    wl = _load()
    cmd = wl.revert()
    click.echo(cmd)

    if cmd.startswith("echo '[loop-state] No revert"):
        sys.exit(1)


# ---------------------------------------------------------------------------
# log
# ---------------------------------------------------------------------------

@main.command()
@click.option("--status", type=click.Choice(["kept", "reverted"]), required=True)
@click.option("--summary", required=True, help="What happened this attempt.")
@click.option("--phase", default="", help="Loop phase name (optional).")
def log(status: str, summary: str, phase: str) -> None:
    """Record an attempt in the work log."""
    wl = _load()
    wl.record_attempt(status=status, summary=summary, phase=phase)
    click.echo(
        f"Logged attempt {wl.attempts_made}: {status} — {summary[:60]}"
    )


# ---------------------------------------------------------------------------
# anti-pattern
# ---------------------------------------------------------------------------

@main.command("anti-pattern")
@click.option("--pattern", required=True, help="Short name for the pattern.")
@click.option("--root-cause", required=True, help="Why this bug existed.")
@click.option("--file", required=True, help="File path where the bug was.")
@click.option("--line", type=int, required=True, help="Line number.")
@click.option("--rule", required=True, help="Prevention rule to avoid recurrence.")
def anti_pattern_cmd(
    pattern: str, root_cause: str, file: str, line: int, rule: str
) -> None:
    """Record an anti-pattern (post-mortem)."""
    wl = _load()
    wl.record_anti_pattern(
        pattern=pattern,
        root_cause=root_cause,
        file=file,
        line=line,
        prevention_rule=rule,
    )
    click.echo(f"Anti-pattern recorded: {pattern}")


# ---------------------------------------------------------------------------
# check-anti-patterns
# ---------------------------------------------------------------------------

@main.command("check-anti-patterns")
@click.option("--module", default=None, help="Filter by module / file substring.")
def check_anti_patterns(module: Optional[str]) -> None:
    """Query anti-patterns (optionally filtered by module)."""
    wl = _load()
    aps = wl.get_anti_patterns(for_module=module)
    click.echo(json.dumps(aps, indent=2))


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

@main.command()
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def status(as_json: bool) -> None:
    """Print current loop state."""
    wl = _load()
    if as_json:
        click.echo(json.dumps(wl.to_dict(), indent=2))
    else:
        d = wl.to_dict()
        click.echo(f"Task:      {d['task_id']}")
        click.echo(f"Loop:      {d['loop_type']}")
        click.echo(f"Attempts:  {d['attempts_made']} / {d['max_attempts']}")
        click.echo(f"Green ref: {d['last_green_commit'] or '(none)'}")
        click.echo(f"History:   {len(d['history'])} entries")
        click.echo(f"Anti-pat:  {len(d['anti_patterns'])} patterns")


# ---------------------------------------------------------------------------
# backup
# ---------------------------------------------------------------------------

@main.command()
def backup() -> None:
    """Snapshot the working tree as a revert point."""
    wl = _load()
    ref = wl.backup_current()
    click.echo(f"Backup: {ref}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()
