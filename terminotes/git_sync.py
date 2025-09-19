"""Integration with Git for syncing the notes repository."""

from __future__ import annotations

import subprocess
from pathlib import Path


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
