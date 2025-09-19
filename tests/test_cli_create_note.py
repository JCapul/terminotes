"""Tests for the Click-based Terminotes CLI."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from click.testing import CliRunner

from terminotes.cli import cli
from terminotes.git_sync import GitSync
from terminotes.storage import DB_FILENAME


def _write_config(base_dir: Path) -> Path:
    config_path = base_dir / "config.toml"
    config_path.write_text(
        """
notes_repo_url = "file:///tmp/terminotes-notes.git"
allowed_tags = ["til", "python"]
editor = "cat"
        """.strip()
    )
    repo_dir = base_dir / "notes-repo"
    (repo_dir / ".git").mkdir(parents=True)
    return config_path


def test_cli_creates_note_from_message(tmp_path, monkeypatch) -> None:
    config_path = _write_config(tmp_path)
    repo_dir = tmp_path / "notes-repo"
    monkeypatch.setattr(GitSync, "ensure_local_clone", lambda self: None)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--config",
            str(config_path),
            "--tags",
            "til",
            "Message",
            "from",
            "CLI",
        ],
    )

    assert result.exit_code == 0, result.output

    conn = sqlite3.connect(repo_dir / DB_FILENAME)
    row = conn.execute("SELECT content, tags FROM notes").fetchone()
    conn.close()

    assert row is not None
    assert row[0] == "Message from CLI"
    assert tuple(json.loads(row[1])) == ("til",)


def test_cli_uses_editor_when_message_missing(tmp_path, monkeypatch) -> None:
    config_path = _write_config(tmp_path)
    repo_dir = tmp_path / "notes-repo"
    monkeypatch.setattr(GitSync, "ensure_local_clone", lambda self: None)

    def fake_editor(template: str, editor: str | None = None) -> str:
        assert "tags: []" in template
        return (
            "---\n"
            "title: Edited Title\n"
            "tags: [python]\n"
            "---\n\n"
            "Body from editor."
        )

    monkeypatch.setattr("terminotes.cli.open_editor", fake_editor)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--config",
            str(config_path),
        ],
    )

    assert result.exit_code == 0, result.output

    conn = sqlite3.connect(repo_dir / DB_FILENAME)
    row = conn.execute("SELECT content, tags FROM notes").fetchone()
    conn.close()

    assert row is not None
    assert row[0] == "Edited Title\n\nBody from editor."
    assert tuple(json.loads(row[1])) == ("python",)
