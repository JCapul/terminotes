from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from terminotes.git_sync import GitSync, GitSyncError


@pytest.mark.skipif(
    subprocess.call(
        ["git", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    != 0,
    reason="git executable is required for git sync tests",
)
def test_ensure_local_clone_clones_missing_repo(tmp_path: Path) -> None:
    remote = tmp_path / "remote.git"
    _run_git("init", "--bare", str(remote))

    clone_path = tmp_path / "clone"
    sync = GitSync(clone_path, str(remote))
    sync.ensure_local_clone()

    assert (clone_path / ".git").is_dir()


@pytest.mark.skipif(
    subprocess.call(
        ["git", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    != 0,
    reason="git executable is required for git sync tests",
)
def test_ensure_local_clone_validates_remote(tmp_path: Path) -> None:
    remote = tmp_path / "remote.git"
    _run_git("init", "--bare", str(remote))

    clone_path = tmp_path / "clone"
    sync = GitSync(clone_path, str(remote))
    sync.ensure_local_clone()

    other_remote = tmp_path / "other.git"
    _run_git("init", "--bare", str(other_remote))

    mismatch_sync = GitSync(clone_path, str(other_remote))
    with pytest.raises(GitSyncError):
        mismatch_sync.ensure_local_clone()


def _run_git(*args: str) -> None:
    subprocess.run(
        ["git", *args], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
