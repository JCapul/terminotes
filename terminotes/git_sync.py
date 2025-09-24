"""Integration with Git for syncing the notes repository.

This module encapsulates the minimal git operations Terminotes needs
to keep the SQLite database synchronized when a remote is configured.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional


class GitSyncError(RuntimeError):
    """Base error for git synchronization issues."""


class GitSync:
    """Wrapper around Git commands for committing, pushing, and setup tasks."""

    def __init__(self, repo_path: Path, remote_url: str) -> None:
        self.repo_path = repo_path.expanduser()
        self.remote_url = remote_url

    # Stage 4 will extend this class with commit/push behaviour. The Stage 2
    # focus is on ensuring the repository exists locally before use.

    def ensure_local_clone(self) -> None:
        """Clone the remote repository if it does not exist locally and validate it."""

        if self.repo_path.exists():
            if not (self.repo_path / ".git").is_dir():
                raise GitSyncError(
                    f"Existing path '{self.repo_path}' is not a git repository."
                )
            self._verify_origin()
            return

        self.repo_path.parent.mkdir(parents=True, exist_ok=True)
        self._run_git(
            "clone", self.remote_url, str(self.repo_path), cwd=self.repo_path.parent
        )

    # ---------------------------------------------------------------------
    # High-level sync helpers
    # ---------------------------------------------------------------------

    def commit_db_update(self, db_path: Path, message: Optional[str] = None) -> None:
        """Stage the DB file and commit.

        If there are no changes, the commit step is skipped gracefully.
        """

        rel_db = str(db_path)
        self._run_git("add", rel_db)

        # Only commit if something is actually staged for this file
        status = self._run_git("status", "--porcelain", "--", rel_db)
        if not status.strip():
            # No changes detected, skipping commit
            return

        commit_msg = message or "chore(db): update notes database"
        self._run_git("commit", "-m", commit_msg)

    def push_current_branch(self) -> str:
        """Push to origin for the current branch and return the branch name."""

        branch = self.current_branch()
        self._run_git("push", "origin", branch)
        return branch

    def force_push_with_lease(self, branch: str) -> None:
        self._run_git("push", "--force-with-lease", "origin", branch)

    def hard_reset_to_remote(self, branch: str) -> None:
        self._run_git("fetch", "--prune")
        self._run_git("reset", "--hard", f"origin/{branch}")

    def current_branch(self) -> str:
        name = self._run_git("rev-parse", "--abbrev-ref", "HEAD").strip()
        if name in ("HEAD", ""):
            raise GitSyncError("Detached HEAD or unknown branch; cannot push.")
        return name

    # ---------------------------------------------------------------------
    # Capability checks
    # ---------------------------------------------------------------------
    def is_valid_repo(self) -> bool:
        """Return True if the path appears to be a functional git repo."""
        try:
            out = self._run_git("rev-parse", "--is-inside-work-tree")
            return out.strip() == "true"
        except GitSyncError:
            return False

    def is_worktree_clean(self) -> bool:
        """Return True if there are no staged or unstaged changes."""
        out = self._run_git("status", "--porcelain")
        return out.strip() == ""

    # ---------------------------------------------------------------------
    # Remote state & divergence helpers
    # ---------------------------------------------------------------------
    def fetch_prune(self) -> None:
        self._run_git("fetch", "--prune")

    def get_upstream(self) -> str | None:
        """Return the full upstream ref for the current branch, or None."""
        try:
            ref = self._run_git(
                "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"
            ).strip()
            return ref or None
        except GitSyncError:
            return None

    def detect_divergence(self) -> str:
        """Detect local/remote relationship for the current branch.

        Returns one of: 'no_upstream', 'up_to_date', 'local_ahead',
        'remote_ahead', 'diverged'.
        """
        if self.get_upstream() is None:
            return "no_upstream"
        try:
            out = self._run_git("rev-list", "--left-right", "--count", "@{u}...HEAD")
        except GitSyncError:
            # If rev-list fails, treat as diverged conservatively
            return "diverged"
        parts = out.strip().split()
        if len(parts) != 2:
            return "diverged"
        ahead_remote, ahead_local = (int(parts[0]), int(parts[1]))
        if ahead_remote == 0 and ahead_local == 0:
            return "up_to_date"
        if ahead_remote == 0 and ahead_local > 0:
            return "local_ahead"
        if ahead_remote > 0 and ahead_local == 0:
            return "remote_ahead"
        return "diverged"

    def push_set_upstream(self, branch: str) -> None:
        self._run_git("push", "-u", "origin", branch)

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------
    def _verify_origin(self) -> None:
        current_url = self._run_git(
            "config",
            "--get",
            "remote.origin.url",
            cwd=self.repo_path,
        )
        if current_url.strip() != self.remote_url:
            raise GitSyncError(
                "Existing repository remote does not match configured URL. "
                f"Expected '{self.remote_url}', found '{current_url.strip()}'."
            )

    def _run_git(self, *args: str, cwd: Path | None = None) -> str:
        process = subprocess.run(
            ["git", *args],
            cwd=cwd if cwd is not None else self.repo_path,
            capture_output=True,
            text=True,
            check=False,
        )
        if process.returncode != 0:
            args_display = " ".join(args)
            stderr = process.stderr.strip()
            raise GitSyncError(
                f"git {args_display} failed (exit {process.returncode}): {stderr}"
            )
        return process.stdout
