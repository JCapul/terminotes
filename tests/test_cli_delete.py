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
    # Avoid interacting with real git during CLI tests; skip local commits.
    monkeypatch.setattr(
        GitSync, "commit_db_update", lambda self, path, message=None: None
    )


def test_delete_removes_note(tmp_path: Path, monkeypatch) -> None:
    config_path = _write_config(tmp_path)
    repo_dir = tmp_path / "notes-repo"
    _set_default_paths(config_path, monkeypatch)
    monkeypatch.setattr(GitSync, "ensure_local_clone", lambda self: None)

    storage = Storage(repo_dir / DB_FILENAME)
    storage.initialize()
    note = storage.create_note("Title", "Body")

    runner = CliRunner()
    result = runner.invoke(cli.cli, ["delete", "--yes", str(note.id)])
    assert result.exit_code == 0, result.output
    assert f"Deleted note {note.id}" in result.output

    conn = sqlite3.connect(repo_dir / DB_FILENAME)
    row = conn.execute("SELECT COUNT(*) FROM notes").fetchone()
    conn.close()
    assert row is not None and int(row[0]) == 0


def test_delete_nonexistent_fails(tmp_path: Path, monkeypatch) -> None:
    config_path = _write_config(tmp_path)
    repo_dir = tmp_path / "notes-repo"
    _set_default_paths(config_path, monkeypatch)
    monkeypatch.setattr(GitSync, "ensure_local_clone", lambda self: None)

    storage = Storage(repo_dir / DB_FILENAME)
    storage.initialize()

    runner = CliRunner()
    result = runner.invoke(cli.cli, ["delete", "--yes", "9999"])
    assert result.exit_code != 0
    assert "not found" in result.output.lower()


def test_delete_without_yes_prompts_and_can_abort(tmp_path: Path, monkeypatch) -> None:
    config_path = _write_config(tmp_path)
    repo_dir = tmp_path / "notes-repo"
    _set_default_paths(config_path, monkeypatch)
    monkeypatch.setattr(GitSync, "ensure_local_clone", lambda self: None)

    storage = Storage(repo_dir / DB_FILENAME)
    storage.initialize()
    note = storage.create_note("Title", "Body")

    runner = CliRunner()
    # Simulate user declining deletion
    result = runner.invoke(cli.cli, ["delete", str(note.id)], input="n\n")
    assert result.exit_code != 0
    assert "aborted" in result.output.lower()

    # Ensure the note still exists
    conn = sqlite3.connect(repo_dir / DB_FILENAME)
    row = conn.execute("SELECT COUNT(*) FROM notes").fetchone()
    conn.close()
    assert row is not None and int(row[0]) == 1
