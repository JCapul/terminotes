"""Tests for the 'tn log' CLI subcommand."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from click.testing import CliRunner
from terminotes import cli
from terminotes import config as config_module
from terminotes.git_sync import GitSync
from terminotes.storage import DB_FILENAME, Storage
from terminotes.utils.datetime_fmt import parse_user_datetime


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


def _read_single_note(db_path: Path) -> tuple[str, str]:
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT title, body FROM notes").fetchone()
    conn.close()
    assert row is not None
    return row[0], row[1]


def test_log_derives_title_from_first_sentence(tmp_path: Path, monkeypatch) -> None:
    config_path = _write_config(tmp_path)
    repo_dir = tmp_path / "notes-repo"
    _set_default_paths(config_path, monkeypatch)
    monkeypatch.setattr(GitSync, "ensure_local_clone", lambda self: None)

    runner = CliRunner()
    body = "Hello world! Second sentence with more details and #tags. And more."
    result = runner.invoke(cli.cli, ["log", "--", body])
    assert result.exit_code == 0, result.output

    title, stored_body = _read_single_note(repo_dir / DB_FILENAME)
    assert title == "Hello world!"
    assert stored_body == body


def test_log_creates_note_with_body_and_tags(tmp_path: Path, monkeypatch) -> None:
    config_path = _write_config(tmp_path)
    repo_dir = tmp_path / "notes-repo"
    _set_default_paths(config_path, monkeypatch)
    monkeypatch.setattr(GitSync, "ensure_local_clone", lambda self: None)

    runner = CliRunner()
    result = runner.invoke(
        cli.cli, ["log", "--", "This", "is", "a", "log", "#til", "#python"]
    )

    assert result.exit_code == 0, result.output

    title, body = _read_single_note(repo_dir / DB_FILENAME)
    # Title is derived from the first line/sentence when logging directly.
    assert title == "This is a log #til #python"
    assert body == "This is a log #til #python"


def test_log_accepts_explicit_tags(tmp_path: Path, monkeypatch) -> None:
    config_path = _write_config(tmp_path)
    repo_dir = tmp_path / "notes-repo"
    _set_default_paths(config_path, monkeypatch)
    monkeypatch.setattr(GitSync, "ensure_local_clone", lambda self: None)

    runner = CliRunner()
    result = runner.invoke(
        cli.cli,
        ["log", "--tag", "Work", "--tag", "personal", "--", "Tagged entry"],
    )

    assert result.exit_code == 0, result.output

    storage = Storage(repo_dir / DB_FILENAME)
    storage.initialize()
    note = storage.fetch_note(1)
    assert sorted(tag.name for tag in note.tags) == ["log", "personal", "work"]


def test_log_with_message_option_handles_hashtags(tmp_path: Path, monkeypatch) -> None:
    config_path = _write_config(tmp_path)
    repo_dir = tmp_path / "notes-repo"
    _set_default_paths(config_path, monkeypatch)
    monkeypatch.setattr(GitSync, "ensure_local_clone", lambda self: None)

    runner = CliRunner()
    msg = "Crazy stuff happening in #python"
    result = runner.invoke(cli.cli, ["log", "--", msg])

    assert result.exit_code == 0, result.output

    title, body = _read_single_note(repo_dir / DB_FILENAME)
    assert title == msg
    assert body == msg


def test_log_requires_body(tmp_path: Path, monkeypatch) -> None:
    config_path = _write_config(tmp_path)
    _set_default_paths(config_path, monkeypatch)
    monkeypatch.setattr(GitSync, "ensure_local_clone", lambda self: None)

    runner = CliRunner()
    result = runner.invoke(cli.cli, ["log"])  # no content

    assert result.exit_code == 1
    assert "Content is required" in result.output


def test_log_accepts_created_option(tmp_path: Path, monkeypatch) -> None:
    config_path = _write_config(tmp_path)
    repo_dir = tmp_path / "notes-repo"
    _set_default_paths(config_path, monkeypatch)
    monkeypatch.setattr(GitSync, "ensure_local_clone", lambda self: None)
    monkeypatch.setattr(
        GitSync, "commit_db_update", lambda self, path, message=None: None
    )

    runner = CliRunner()
    created_str = "2024-06-15 14:45"
    result = runner.invoke(
        cli.cli,
        ["log", "-c", created_str, "--", "Note with timestamp"],
    )

    assert result.exit_code == 0, result.output

    storage = Storage(repo_dir / DB_FILENAME)
    storage.initialize()
    note = storage.fetch_note(1)
    expected = parse_user_datetime(created_str)
    assert note.created_at == expected
    assert note.updated_at == expected
