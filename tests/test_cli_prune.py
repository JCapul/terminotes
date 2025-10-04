"""Tests for the 'tn prune' CLI subcommand."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from click.testing import CliRunner
from terminotes import cli
from terminotes import config as config_module
from terminotes.git_sync import GitSync
from terminotes.storage import DB_FILENAME, Storage


def _write_config(base_dir: Path) -> Path:
    config_path = base_dir / "config.toml"
    repo_url_line = 'git_remote_url = "file:///tmp/terminotes-notes.git"\n'
    config_path.write_text(
        (f'{repo_url_line}editor = "cat"\n').strip(), encoding="utf-8"
    )
    repo_dir = base_dir / "notes-repo"
    (repo_dir / ".git").mkdir(parents=True)
    return config_path


def _set_default_paths(config_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(config_module, "DEFAULT_CONFIG_PATH", config_path)
    monkeypatch.setattr(config_module, "DEFAULT_CONFIG_DIR", config_path.parent)
    monkeypatch.setattr(cli, "DEFAULT_CONFIG_PATH", config_path)


def _count_tags(db_path: Path) -> int:
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT COUNT(*) FROM tags").fetchone()
    conn.close()
    assert row is not None
    return int(row[0])


def test_prune_skips_when_clean(tmp_path: Path, monkeypatch) -> None:
    config_path = _write_config(tmp_path)
    _set_default_paths(config_path, monkeypatch)
    monkeypatch.setattr(GitSync, "ensure_local_clone", lambda self: None)

    commit_called = False

    def fake_commit(self, path: Path, message: str | None = None) -> None:
        nonlocal commit_called
        commit_called = True

    monkeypatch.setattr(GitSync, "commit_db_update", fake_commit)

    runner = CliRunner()
    result = runner.invoke(cli.cli, ["prune"])

    assert result.exit_code == 0, result.output
    assert "Nothing to prune" in result.output
    assert commit_called is False


def test_prune_removes_orphan_tags(tmp_path: Path, monkeypatch) -> None:
    config_path = _write_config(tmp_path)
    repo_dir = tmp_path / "notes-repo"
    _set_default_paths(config_path, monkeypatch)
    monkeypatch.setattr(GitSync, "ensure_local_clone", lambda self: None)

    storage = Storage(repo_dir / DB_FILENAME)
    storage.initialize()
    note = storage.create_note("Title", "Body", tags=["focus"])
    storage.update_note(note.id, "Title", "Body", tags=[])

    commit_payload: list[str | None] = []

    def fake_commit(self, path: Path, message: str | None = None) -> None:
        commit_payload.append(message)

    monkeypatch.setattr(GitSync, "commit_db_update", fake_commit)

    runner = CliRunner()
    result = runner.invoke(cli.cli, ["prune"])

    assert result.exit_code == 0, result.output
    assert "Pruned 1 tag and 0 orphaned links." in result.output
    assert commit_payload == ["chore(db): prune unused tags"]
    assert _count_tags(repo_dir / DB_FILENAME) == 0
