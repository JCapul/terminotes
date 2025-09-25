"""Tests for the 'tn log' CLI subcommand."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from click.testing import CliRunner
from terminotes import cli
from terminotes import config as config_module
from terminotes.git_sync import GitSync
from terminotes.storage import DB_FILENAME


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


def _read_single_note(db_path: Path) -> tuple[str, str, tuple[str, ...], str]:
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT title, body, tags, type FROM notes").fetchone()
    conn.close()
    assert row is not None
    return row[0], row[1], tuple(json.loads(row[2])), str(row[3])


def test_log_creates_note_with_body_and_tags(tmp_path: Path, monkeypatch) -> None:
    config_path = _write_config(tmp_path)
    repo_dir = tmp_path / "notes-repo"
    _set_default_paths(config_path, monkeypatch)
    monkeypatch.setattr(GitSync, "ensure_local_clone", lambda self: None)

    runner = CliRunner()
    result = runner.invoke(
        cli.cli, ["log", "-t", "til,python", "--", "This", "is", "a", "log"]
    )

    assert result.exit_code == 0, result.output

    title, body, tags, note_type = _read_single_note(repo_dir / DB_FILENAME)
    assert title == ""
    assert body == "This is a log"
    assert tags == ("til", "python")
    assert note_type == "log"


def test_log_requires_body(tmp_path: Path, monkeypatch) -> None:
    config_path = _write_config(tmp_path)
    _set_default_paths(config_path, monkeypatch)
    monkeypatch.setattr(GitSync, "ensure_local_clone", lambda self: None)

    runner = CliRunner()
    result = runner.invoke(cli.cli, ["log"])  # no content

    assert result.exit_code == 1
    assert "Body is required" in result.output


def test_log_accepts_any_tags(tmp_path: Path, monkeypatch) -> None:
    config_path = _write_config(tmp_path)
    repo_dir = tmp_path / "notes-repo"
    _set_default_paths(config_path, monkeypatch)
    monkeypatch.setattr(GitSync, "ensure_local_clone", lambda self: None)

    runner = CliRunner()
    result = runner.invoke(cli.cli, ["log", "-t", "not-allowed", "--", "Body"])

    assert result.exit_code == 0, result.output
    title, body, tags, note_type = _read_single_note(repo_dir / DB_FILENAME)
    assert title == ""
    assert body == "Body"
    assert tags == ("not-allowed",)
    assert note_type == "log"


def test_log_parses_repeated_and_csv_tags(tmp_path: Path, monkeypatch) -> None:
    config_path = _write_config(tmp_path)
    repo_dir = tmp_path / "notes-repo"
    _set_default_paths(config_path, monkeypatch)
    monkeypatch.setattr(GitSync, "ensure_local_clone", lambda self: None)

    runner = CliRunner()
    result = runner.invoke(
        cli.cli,
        ["log", "-t", "til", "-t", "python", "--", "Body"],
    )

    assert result.exit_code == 0, result.output

    _, _, tags, note_type = _read_single_note(repo_dir / DB_FILENAME)
    assert tags == ("til", "python")
    assert note_type == "log"
