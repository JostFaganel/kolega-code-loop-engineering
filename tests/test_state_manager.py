"""Unit tests for kolega_loop_state.state_manager."""

import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest

from kolega_loop_state.state_manager import (
    AttemptLimitExceeded,
    WorkLog,
    DEFAULT_TEMPLATE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_workdir():
    """Create a temporary directory and cd into it for each test."""
    old = os.getcwd()
    with tempfile.TemporaryDirectory() as td:
        os.chdir(td)
        yield Path(td)
        os.chdir(old)


@pytest.fixture
def git_repo(tmp_workdir):
    """Create a git repo so last_green_commit works."""
    subprocess.run(["git", "init"], check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        check=True,
        capture_output=True,
    )
    # Create an initial commit so HEAD exists
    Path("README.md").write_text("# test")
    subprocess.run(["git", "add", "README.md"], check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"], check=True, capture_output=True
    )
    return tmp_workdir


def _wl_path() -> str:
    return str(Path(os.getcwd()) / "work-log.json")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestInit:
    def test_creates_work_log(self, tmp_workdir):
        """loop-state init creates valid work-log.json."""
        wl = WorkLog.load(_wl_path())
        wl._data["task_id"] = "test-1"
        wl._data["loop_type"] = "new-code"
        wl._data["max_attempts"] = 3
        wl.save()

        assert Path(_wl_path()).exists()
        data = json.loads(Path(_wl_path()).read_text())
        assert data["task_id"] == "test-1"
        assert data["loop_type"] == "new-code"
        assert data["max_attempts"] == 3
        assert data["attempts_made"] == 0

    def test_creates_from_scratch(self, tmp_workdir):
        """Load creates file when none exists."""
        assert not Path(_wl_path()).exists()
        wl = WorkLog.load(_wl_path())
        assert Path(_wl_path()).exists()
        assert wl.attempts_made == 0


class TestAttempt:
    def test_increments(self, tmp_workdir):
        wl = WorkLog.load(_wl_path())
        wl._data["task_id"] = "test"
        wl._data["max_attempts"] = 3
        wl.save()

        n = wl.inc_attempt()
        assert n == 1
        assert wl.attempts_made == 1

        n = wl.inc_attempt()
        assert n == 2

    def test_limit_exceeded(self, tmp_workdir):
        wl = WorkLog.load(_wl_path())
        wl._data["task_id"] = "test"
        wl._data["max_attempts"] = 2
        wl.save()

        wl.inc_attempt()  # 1
        wl.inc_attempt()  # 2  — now at limit
        with pytest.raises(AttemptLimitExceeded) as exc:
            wl.inc_attempt()  # 3 — over
        assert exc.value.attempts_made == 3
        assert exc.value.max_attempts == 2


class TestLog:
    def test_kept_updates_green(self, git_repo):
        wl = WorkLog.load(_wl_path())
        wl._data["task_id"] = "test"
        wl._data["max_attempts"] = 3
        wl.inc_attempt()

        wl.record_attempt(status="kept", summary="All good", phase="generate")
        assert wl._data["last_green_commit"] is not None
        assert len(wl._data["history"]) == 1
        assert wl._data["history"][0]["status"] == "kept"

    def test_reverted_no_green_update(self, git_repo):
        # Ensure clean state
        Path(_wl_path()).unlink(missing_ok=True)
        wl = WorkLog.load(_wl_path())
        wl._data["task_id"] = "test"
        wl._data["max_attempts"] = 3
        wl._data["last_green_commit"] = "abc123"
        wl.inc_attempt()

        wl.record_attempt(
            status="reverted", summary="Tests failed", phase="verify"
        )
        # last_green_commit should NOT change on revert
        assert wl._data["last_green_commit"] == "abc123"

        # Reload from disk to prove persistence
        wl2 = WorkLog.load(_wl_path())
        assert wl2._data["history"][-1]["status"] == "reverted"

    def test_sub_agent_ids_recorded(self, git_repo):
        # Ensure clean state
        Path(_wl_path()).unlink(missing_ok=True)
        wl = WorkLog.load(_wl_path())
        wl._data["task_id"] = "test"
        wl._data["max_attempts"] = 3
        wl.inc_attempt()

        wl.record_attempt(
            status="kept",
            summary="done",
            sub_agent_ids=["gen-1", "gen-2", "ver-1"],
        )

        # Reload from disk to prove persistence
        wl2 = WorkLog.load(_wl_path())
        assert wl2._data["history"][-1]["sub_agent_ids"] == [
            "gen-1", "gen-2", "ver-1"
        ]


class TestRevert:
    def test_git_mode(self, git_repo):
        wl = WorkLog.load(_wl_path())
        wl._data["task_id"] = "test"
        wl._data["last_green_commit"] = "deadbeef"
        wl.save()

        cmd = wl.revert()
        assert "git reset --hard deadbeef" in cmd

    def test_no_git_mode(self, tmp_workdir):
        # Create a fake backup directory
        backup = str(tmp_workdir / ".loop-backup-test")
        os.makedirs(backup)

        wl = WorkLog.load(_wl_path())
        wl._data["task_id"] = "test"
        wl._data["last_green_backup"] = backup
        wl.save()

        cmd = wl.revert()
        assert "rsync" in cmd
        assert ".loop-backup-test" in cmd

    def test_no_revert_point(self, tmp_workdir):
        wl = WorkLog.load(_wl_path())
        wl._data["task_id"] = "test"
        wl.save()

        cmd = wl.revert()
        assert "No revert point" in cmd


class TestBackup:
    def test_git_mode(self, git_repo):
        wl = WorkLog.load(_wl_path())
        wl._data["task_id"] = "test"
        wl.save()

        ref = wl.backup_current()
        assert ref is not None
        assert len(ref) == 40  # SHA-1 hash

    def test_no_git_mode(self, tmp_workdir):
        # Create a file to be backed up
        Path("src").mkdir()
        Path("src/app.py").write_text("print('hello')")

        wl = WorkLog.load(_wl_path())
        wl._data["task_id"] = "test"
        wl.save()

        ref = wl.backup_current()
        assert ".loop-backup-test" in ref
        assert os.path.isdir(ref)
        assert os.path.isfile(os.path.join(ref, "src", "app.py"))


class TestAntiPatterns:
    def test_record_and_query(self, tmp_workdir):
        wl = WorkLog.load(_wl_path())
        wl._data["task_id"] = "test"
        wl.save()

        wl.record_anti_pattern(
            pattern="zero-div-empty-string",
            root_cause="No guard on empty input",
            file="src/calc.py",
            line=42,
            prevention_rule="Validate inputs before arithmetic",
        )

        aps = wl.get_anti_patterns()
        assert len(aps) == 1
        assert aps[0]["pattern"] == "zero-div-empty-string"
        assert aps[0]["occurrence_count"] == 1

    def test_filter_by_module(self, tmp_workdir):
        wl = WorkLog.load(_wl_path())
        wl._data["task_id"] = "test"
        wl.save()

        wl.record_anti_pattern(
            pattern="bad-auth",
            root_cause="test",
            file="src/services/auth.py",
            line=1,
            prevention_rule="test",
        )
        wl.record_anti_pattern(
            pattern="bad-ledger",
            root_cause="test",
            file="src/services/ledger.py",
            line=1,
            prevention_rule="test",
        )

        aps = wl.get_anti_patterns(for_module="auth")
        assert len(aps) == 1
        assert aps[0]["pattern"] == "bad-auth"

        aps = wl.get_anti_patterns(for_module="zed")
        assert len(aps) == 0

    def test_deduplication(self, tmp_workdir):
        # Ensure clean state
        Path(_wl_path()).unlink(missing_ok=True)
        wl = WorkLog.load(_wl_path())
        wl._data["task_id"] = "test"
        wl.save()

        wl.record_anti_pattern(
            pattern="race-on-init",
            root_cause="Flag after await",
            file="src/svc.py",
            line=10,
            prevention_rule="Set flags synchronously",
        )
        wl.record_anti_pattern(
            pattern="race-on-init",  # same pattern
            root_cause="Flag after await",
            file="src/svc.py",
            line=10,
            prevention_rule="Set flags synchronously",
        )

        aps = wl.get_anti_patterns()
        assert len(aps) == 1  # not duplicated
        assert aps[0]["occurrence_count"] == 2


class TestAtomicSave:
    def test_atomic_save(self, tmp_workdir):
        wl = WorkLog.load(_wl_path())
        wl._data["task_id"] = "atomic"
        wl._data["loop_type"] = "bug-fix"
        wl.save()

        # Reload and verify
        wl2 = WorkLog.load(_wl_path())
        assert wl2._data["task_id"] == "atomic"


class TestCorruptedRecovery:
    def test_corrupted_json(self, tmp_workdir):
        Path(_wl_path()).write_text("not valid json {{{")

        wl = WorkLog.load(_wl_path())
        # Should have reinitialized to defaults
        assert wl._data["version"] == "1.0"
        assert wl._data["task_id"] is None
