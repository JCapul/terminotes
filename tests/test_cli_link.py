"""Tests for the `tn link` command."""

from __future__ import annotations

import json
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
        (f'{repo_url_line}editor = "cat"\nterminotes_dir = "notes-repo"\n').strip(),
        encoding="utf-8",
    )
    (base_dir / "notes-repo" / ".git").mkdir(parents=True)
    return config_path


def _set_default_paths(config_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(config_module, "DEFAULT_CONFIG_PATH", config_path)
    monkeypatch.setattr(config_module, "DEFAULT_CONFIG_DIR", config_path.parent)
    monkeypatch.setattr(cli, "DEFAULT_CONFIG_PATH", config_path)


def test_link_command_stores_snapshot(tmp_path, monkeypatch) -> None:
    config_path = _write_config(tmp_path)
    repo_dir = tmp_path / "notes-repo"

    _set_default_paths(config_path, monkeypatch)
    monkeypatch.setattr(GitSync, "ensure_local_clone", lambda self: None)
    monkeypatch.setattr(
        GitSync, "commit_db_update", lambda self, path, message=None: None
    )

    snapshot = {
        "url": "https://web.archive.org/web/20240101000000/https://example.com/",
        "timestamp": "20240101000000",
    }
    monkeypatch.setattr(
        "terminotes.services.notes.fetch_latest_snapshot",
        lambda _url: snapshot,
    )
    monkeypatch.setattr(
        "terminotes.services.notes.get_page_title",
        lambda _url: "Example Title",
    )

    runner = CliRunner()
    result = runner.invoke(
        cli.cli,
        ["link", "https://example.com", "Interesting", "article"],
    )

    assert result.exit_code == 0, result.output
    assert "Wayback fallback" in result.output

    storage = Storage(repo_dir / DB_FILENAME)
    storage.initialize()
    saved = storage.fetch_note(1)
    assert saved.title == "Example Title (example.com)"
    assert json.loads(saved.extra_data)["link"]["wayback"] == snapshot["url"]
    assert sorted(tag.name for tag in saved.tags) == ["link"]


def test_link_command_handles_missing_snapshot(tmp_path, monkeypatch) -> None:
    config_path = _write_config(tmp_path)
    repo_dir = tmp_path / "notes-repo"

    _set_default_paths(config_path, monkeypatch)
    monkeypatch.setattr(GitSync, "ensure_local_clone", lambda self: None)
    monkeypatch.setattr(
        GitSync, "commit_db_update", lambda self, path, message=None: None
    )

    monkeypatch.setattr(
        "terminotes.services.notes.fetch_latest_snapshot",
        lambda _url: None,
    )
    monkeypatch.setattr(
        "terminotes.services.notes.get_page_title",
        lambda _url: None,
    )

    runner = CliRunner()
    result = runner.invoke(cli.cli, ["link", "https://example.com"])

    assert result.exit_code == 0, result.output
    assert "No Wayback snapshot" in result.output

    storage = Storage(repo_dir / DB_FILENAME)
    storage.initialize()
    saved = storage.fetch_note(1)
    assert saved.title == "https://example.com"
    extra = saved.extra_data
    assert extra is not None
    data = json.loads(extra)
    assert data["link"]["wayback"] is None


def test_link_command_uses_page_title(tmp_path, monkeypatch) -> None:
    config_path = _write_config(tmp_path)
    repo_dir = tmp_path / "notes-repo"

    _set_default_paths(config_path, monkeypatch)
    monkeypatch.setattr(GitSync, "ensure_local_clone", lambda self: None)
    monkeypatch.setattr(
        GitSync, "commit_db_update", lambda self, path, message=None: None
    )

    monkeypatch.setattr(
        "terminotes.services.notes.fetch_latest_snapshot",
        lambda _url: None,
    )
    monkeypatch.setattr(
        "terminotes.services.notes.get_page_title",
        lambda _url: "Example Title",
    )

    runner = CliRunner()
    result = runner.invoke(cli.cli, ["link", "https://example.com"])

    assert result.exit_code == 0, result.output

    storage = Storage(repo_dir / DB_FILENAME)
    storage.initialize()
    saved = storage.fetch_note(1)
    assert saved.title == "Example Title (example.com)"


def test_link_accepts_created_option(tmp_path, monkeypatch) -> None:
    config_path = _write_config(tmp_path)
    repo_dir = tmp_path / "notes-repo"

    _set_default_paths(config_path, monkeypatch)
    monkeypatch.setattr(GitSync, "ensure_local_clone", lambda self: None)
    monkeypatch.setattr(
        GitSync, "commit_db_update", lambda self, path, message=None: None
    )

    monkeypatch.setattr(
        "terminotes.services.notes.fetch_latest_snapshot",
        lambda _url: None,
    )
    monkeypatch.setattr(
        "terminotes.services.notes.get_page_title",
        lambda _url: None,
    )

    runner = CliRunner()
    created_str = "2024-06-15 14:45"
    result = runner.invoke(
        cli.cli,
        ["link", "-c", created_str, "https://example.com"],
    )

    assert result.exit_code == 0, result.output

    storage = Storage(repo_dir / DB_FILENAME)
    storage.initialize()
    note = storage.fetch_note(1)
    expected = parse_user_datetime(created_str)
    assert note.created_at == expected
    assert note.updated_at == expected
