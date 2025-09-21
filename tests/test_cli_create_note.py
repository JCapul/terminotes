"""Tests for the Click-based Terminotes CLI commands."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

import yaml
from click.testing import CliRunner

from terminotes import cli
from terminotes import config as config_module
from terminotes.git_sync import GitSync
from terminotes.storage import DB_FILENAME, Storage


def _write_config(base_dir: Path, *, git_enabled: bool = True) -> Path:
    config_path = base_dir / "config.toml"
    repo_url_line = (
        'notes_repo_url = "file:///tmp/terminotes-notes.git"\n'
        if git_enabled
        else 'notes_repo_url = ""\n'
    )
    config_path.write_text(
        (
            f"{repo_url_line}"
            "allowed_tags = [\"til\", \"python\"]\n"
            'editor = "cat"\n'
        ).strip(),
        encoding="utf-8",
    )
    repo_dir = base_dir / "notes-repo"
    (repo_dir / ".git").mkdir(parents=True)
    return config_path


def _set_default_paths(config_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(config_module, "DEFAULT_CONFIG_PATH", config_path)
    monkeypatch.setattr(config_module, "DEFAULT_CONFIG_DIR", config_path.parent)
    monkeypatch.setattr(cli, "DEFAULT_CONFIG_PATH", config_path)


def _read_single_note(db_path: Path) -> tuple[str, tuple[str, ...]]:
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT content, tags FROM notes").fetchone()
    conn.close()
    assert row is not None
    return row[0], tuple(json.loads(row[1]))


def test_new_command_creates_note_with_metadata(tmp_path, monkeypatch) -> None:
    config_path = _write_config(tmp_path)
    repo_dir = tmp_path / "notes-repo"
    _set_default_paths(config_path, monkeypatch)
    monkeypatch.setattr(GitSync, "ensure_local_clone", lambda self: None)

    captured_template: dict[str, str] = {}

    def fake_editor(template: str, editor: str | None = None) -> str:
        captured_template["value"] = template
        return (
            "---\n"
            "title: Captured Title\n"
            "date: 2024-01-01T12:00:00+00:00\n"
            "last_edited: 2024-01-01T12:00:00+00:00\n"
            "tags:\n"
            "  - til\n"
            "  - python\n"
            "---\n\n"
            "Body from editor.\n"
        )

    monkeypatch.setattr("terminotes.cli.open_editor", fake_editor)

    runner = CliRunner()
    result = runner.invoke(
        cli.cli,
        [
            "new",
        ],
    )

    assert result.exit_code == 0, result.output

    template = captured_template["value"]
    metadata_block = template.split("---\n", 2)[1].split("\n---", 1)[0]
    metadata = yaml.safe_load(metadata_block)
    assert "date" in metadata
    assert "last_edited" in metadata

    content, tags = _read_single_note(repo_dir / DB_FILENAME)
    assert content == "Captured Title\n\nBody from editor."
    assert tags == ("til", "python")


def test_edit_command_updates_note_and_metadata(tmp_path, monkeypatch) -> None:
    config_path = _write_config(tmp_path)
    repo_dir = tmp_path / "notes-repo"
    _set_default_paths(config_path, monkeypatch)
    monkeypatch.setattr(GitSync, "ensure_local_clone", lambda self: None)

    storage = Storage(repo_dir / DB_FILENAME)
    storage.initialize()
    note = storage.create_note("Existing Title\n\nBody", ["til"])

    captured_template: dict[str, str] = {}

    def fake_editor(template: str, editor: str | None = None) -> str:
        captured_template["value"] = template
        return (
            "---\n"
            "title: Updated Title\n"
            f"date: {note.created_at.isoformat()}\n"
            f"last_edited: {datetime.now().isoformat()}\n"
            "tags:\n"
            "  - python\n"
            "---\n\n"
            "Updated body.\n"
        )

    monkeypatch.setattr("terminotes.cli.open_editor", fake_editor)

    runner = CliRunner()
    result = runner.invoke(
        cli.cli,
        [
            "edit",
            note.note_id,
        ],
    )

    assert result.exit_code == 0, result.output

    template = captured_template["value"]
    metadata_block = template.split("---\n", 2)[1].split("\n---", 1)[0]
    metadata = yaml.safe_load(metadata_block)
    assert metadata["title"] == "Existing Title"
    assert "last_edited" in metadata

    content, tags = _read_single_note(repo_dir / DB_FILENAME)
    assert content == "Updated Title\n\nUpdated body."
    assert tags == ("python",)


def test_edit_without_note_id_uses_last_updated(tmp_path, monkeypatch) -> None:
    config_path = _write_config(tmp_path)
    repo_dir = tmp_path / "notes-repo"
    _set_default_paths(config_path, monkeypatch)
    monkeypatch.setattr(GitSync, "ensure_local_clone", lambda self: None)

    storage = Storage(repo_dir / DB_FILENAME)
    storage.initialize()
    first = storage.create_note("First title\n\nFirst body", ["til"])
    second = storage.create_note("Second title\n\nSecond body", ["python"])

    storage.update_note(first.note_id, "First title\n\nFirst body updated", ["til"])

    captured_template: dict[str, str] = {}

    def fake_editor(template: str, editor: str | None = None) -> str:
        captured_template["value"] = template
        return (
            "---\n"
            "title: First title updated\n"
            f"date: {first.created_at.isoformat()}\n"
            f"last_edited: {datetime.now().isoformat()}\n"
            "tags:\n"
            "  - python\n"
            "---\n\n"
            "First body updated via edit.\n"
        )

    monkeypatch.setattr("terminotes.cli.open_editor", fake_editor)

    runner = CliRunner()
    result = runner.invoke(
        cli.cli,
        ["edit"],
    )

    assert result.exit_code == 0, result.output

    template = captured_template["value"]
    metadata_block = template.split("---\n", 2)[1].split("\n---", 1)[0]
    metadata = yaml.safe_load(metadata_block)
    assert metadata["title"] == "First title"

    conn = sqlite3.connect(repo_dir / DB_FILENAME)
    row = conn.execute(
        "SELECT content, tags FROM notes WHERE note_id = ?",
        (first.note_id,),
    ).fetchone()
    conn.close()

    assert row is not None
    assert row[0] == "First title updated\n\nFirst body updated via edit."
    assert tuple(json.loads(row[1])) == ("python",)

def test_config_command_bootstraps_when_missing(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "config" / "config.toml"
    _set_default_paths(config_path, monkeypatch)
    monkeypatch.setattr(GitSync, "ensure_local_clone", lambda self: None)

    edited_paths: list[str] = []

    def fake_edit(*, filename: str | None = None, editor: str | None = None, text=None, env=None, require_save=True):
        if filename is not None:
            edited_paths.append(filename)
        return None

    monkeypatch.setattr("terminotes.cli.click.edit", fake_edit)

    runner = CliRunner()
    result = runner.invoke(
        cli.cli,
        ["config"],
    )

    assert result.exit_code == 0, result.output
    assert edited_paths == [str(config_path)]
    assert config_path.exists()


def test_new_command_without_git_sync(tmp_path, monkeypatch) -> None:
    config_path = _write_config(tmp_path, git_enabled=False)
    repo_dir = tmp_path / "notes-repo"
    _set_default_paths(config_path, monkeypatch)

    class ShouldNotRunGit(GitSync):
        def __init__(self, *args, **kwargs):  # pragma: no cover - defensive
            raise AssertionError("GitSync should not be instantiated when git sync is disabled")

    monkeypatch.setattr(cli, "GitSync", ShouldNotRunGit)

    def fake_editor(template: str, editor: str | None = None) -> str:
        return (
            "---\n"
            "title: No Backup\n"
            "last_edited: 2024-01-01T00:00:00+00:00\n"
            "date: 2024-01-01T00:00:00+00:00\n"
            "tags: []\n"
            "---\n\n"
            "Body.\n"
        )

    monkeypatch.setattr("terminotes.cli.open_editor", fake_editor)

    runner = CliRunner()
    result = runner.invoke(cli.cli, ["new"])

    assert result.exit_code == 0, result.output

    content, tags = _read_single_note(repo_dir / DB_FILENAME)
    assert content == "No Backup\n\nBody."
    assert tags == ()


def test_info_command_displays_repo_and_config(tmp_path, monkeypatch, capsys) -> None:
    config_path = _write_config(tmp_path)
    repo_dir = tmp_path / "notes-repo"
    _set_default_paths(config_path, monkeypatch)
    monkeypatch.setattr(GitSync, "ensure_local_clone", lambda self: None)

    storage = Storage(repo_dir / DB_FILENAME)
    storage.initialize()
    storage.create_note("Info title\n\nInfo body", ["til"])

    runner = CliRunner()
    result = runner.invoke(cli.cli, ["info"])

    assert result.exit_code == 0, result.output
    output = result.output
    assert "Database file" in output
    assert "Total notes" in output
    assert "Last edited" in output
    assert "notes_repo_url" in output
