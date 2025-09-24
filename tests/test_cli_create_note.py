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
    repo_url_line = 'git_remote_url = "file:///tmp/terminotes-notes.git"\n'
    config_path.write_text(
        (f'{repo_url_line}allowed_tags = ["til", "python"]\neditor = "cat"\n').strip(),
        encoding="utf-8",
    )
    repo_dir = base_dir / "notes-repo"
    (repo_dir / ".git").mkdir(parents=True)
    return config_path


def _set_default_paths(config_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(config_module, "DEFAULT_CONFIG_PATH", config_path)
    monkeypatch.setattr(config_module, "DEFAULT_CONFIG_DIR", config_path.parent)
    monkeypatch.setattr(cli, "DEFAULT_CONFIG_PATH", config_path)


def _read_single_note(db_path: Path) -> tuple[str, str, tuple[str, ...]]:
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT title, body, tags FROM notes").fetchone()
    conn.close()
    assert row is not None
    return row[0], row[1], tuple(json.loads(row[2]))


def _read_single_note_timestamps(db_path: Path) -> tuple[datetime, datetime]:
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT created_at, updated_at FROM notes").fetchone()
    conn.close()
    assert row is not None
    return datetime.fromisoformat(row[0]), datetime.fromisoformat(row[1])


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

    title, body, tags = _read_single_note(repo_dir / DB_FILENAME)
    assert title == "Captured Title"
    assert body == "Body from editor."
    assert tags == ("til", "python")


def test_new_command_respects_custom_timestamps(tmp_path, monkeypatch) -> None:
    config_path = _write_config(tmp_path)
    repo_dir = tmp_path / "notes-repo"
    _set_default_paths(config_path, monkeypatch)
    monkeypatch.setattr(GitSync, "ensure_local_clone", lambda self: None)

    created = "2023-01-01T00:00:00+00:00"
    updated = "2023-02-02T10:00:00+00:00"

    def fake_editor(template: str, editor: str | None = None) -> str:
        return (
            "---\n"
            "title: Has Timestamps\n"
            f"date: {created}\n"
            f"last_edited: {updated}\n"
            "tags: []\n"
            "---\n\n"
            "Body.\n"
        )

    monkeypatch.setattr("terminotes.cli.open_editor", fake_editor)

    runner = CliRunner()
    result = runner.invoke(cli.cli, ["new"])
    assert result.exit_code == 0, result.output

    created_at, updated_at = _read_single_note_timestamps(repo_dir / DB_FILENAME)
    assert created_at == datetime.fromisoformat(created)
    assert updated_at == datetime.fromisoformat(updated)


def test_edit_command_updates_note_and_metadata(tmp_path, monkeypatch) -> None:
    config_path = _write_config(tmp_path)
    repo_dir = tmp_path / "notes-repo"
    _set_default_paths(config_path, monkeypatch)
    monkeypatch.setattr(GitSync, "ensure_local_clone", lambda self: None)

    storage = Storage(repo_dir / DB_FILENAME)
    storage.initialize()
    note = storage.create_note("Existing Title", "Body", ["til"])

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
            str(note.id),
        ],
    )

    assert result.exit_code == 0, result.output

    template = captured_template["value"]
    metadata_block = template.split("---\n", 2)[1].split("\n---", 1)[0]
    metadata = yaml.safe_load(metadata_block)
    assert metadata["title"] == "Existing Title"
    assert "last_edited" in metadata

    title, body, tags = _read_single_note(repo_dir / DB_FILENAME)
    assert title == "Updated Title"
    assert body == "Updated body."
    assert tags == ("python",)


def test_edit_command_allows_changing_timestamps(tmp_path, monkeypatch) -> None:
    config_path = _write_config(tmp_path)
    repo_dir = tmp_path / "notes-repo"
    _set_default_paths(config_path, monkeypatch)
    monkeypatch.setattr(GitSync, "ensure_local_clone", lambda self: None)

    storage = Storage(repo_dir / DB_FILENAME)
    storage.initialize()
    note = storage.create_note("Title", "Body", ["til"])

    new_created = "2020-05-05T05:05:05+00:00"
    new_updated = "2021-06-06T06:06:06+00:00"

    def fake_editor(template: str, editor: str | None = None) -> str:
        return (
            "---\n"
            "title: Title\n"
            f"date: {new_created}\n"
            f"last_edited: {new_updated}\n"
            "tags:\n"
            "  - til\n"
            "---\n\n"
            "Body updated.\n"
        )

    monkeypatch.setattr("terminotes.cli.open_editor", fake_editor)

    runner = CliRunner()
    result = runner.invoke(cli.cli, ["edit", str(note.id)])
    assert result.exit_code == 0, result.output

    conn = sqlite3.connect(repo_dir / DB_FILENAME)
    row = conn.execute(
        "SELECT created_at, updated_at FROM notes WHERE id = ?",
        (note.id,),
    ).fetchone()
    conn.close()
    assert row is not None
    assert datetime.fromisoformat(row[0]) == datetime.fromisoformat(new_created)
    assert datetime.fromisoformat(row[1]) == datetime.fromisoformat(new_updated)


def test_edit_without_note_id_uses_last_updated(tmp_path, monkeypatch) -> None:
    config_path = _write_config(tmp_path)
    repo_dir = tmp_path / "notes-repo"
    _set_default_paths(config_path, monkeypatch)
    monkeypatch.setattr(GitSync, "ensure_local_clone", lambda self: None)

    storage = Storage(repo_dir / DB_FILENAME)
    storage.initialize()
    first = storage.create_note("First title", "First body", ["til"])
    storage.create_note("Second title", "Second body", ["python"])

    storage.update_note(first.id, "First title", "First body updated", ["til"])

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
        "SELECT title, body, tags FROM notes WHERE id = ?",
        (first.id,),
    ).fetchone()
    conn.close()

    assert row is not None
    assert row[0] == "First title updated"
    assert row[1] == "First body updated via edit."
    assert tuple(json.loads(row[2])) == ("python",)


def test_config_command_bootstraps_when_missing(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "config" / "config.toml"
    _set_default_paths(config_path, monkeypatch)
    monkeypatch.setattr(GitSync, "ensure_local_clone", lambda self: None)

    edited_paths: list[str] = []

    def fake_edit(
        *,
        filename: str | None = None,
        editor: str | None = None,
        text=None,
        env=None,
        require_save=True,
    ):
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


## Git URL is now mandatory; local-only mode removed.


def test_new_command_unknown_tags_warns_and_saves_without_tags(
    tmp_path, monkeypatch
) -> None:
    # Only 'til' is allowed, editor will return an unknown tag
    config_path = _write_config(tmp_path)
    repo_dir = tmp_path / "notes-repo"
    _set_default_paths(config_path, monkeypatch)
    monkeypatch.setattr(GitSync, "ensure_local_clone", lambda self: None)

    def fake_editor(template: str, editor: str | None = None) -> str:
        return (
            "---\n"
            "title: Unknown Tags\n"
            "last_edited: 2024-01-01T00:00:00+00:00\n"
            "date: 2024-01-01T00:00:00+00:00\n"
            "tags:\n"
            "  - not-allowed\n"
            "---\n\n"
            "Body.\n"
        )

    monkeypatch.setattr("terminotes.cli.open_editor", fake_editor)

    runner = CliRunner()
    result = runner.invoke(cli.cli, ["new"])

    assert result.exit_code == 0, result.output
    assert "Warning:" in result.output

    title, body, tags = _read_single_note(repo_dir / DB_FILENAME)
    assert title == "Unknown Tags"
    assert body == "Body."
    assert tags == ()


def test_new_command_mixed_tags_keeps_valid(tmp_path, monkeypatch) -> None:
    config_path = _write_config(tmp_path)
    repo_dir = tmp_path / "notes-repo"
    _set_default_paths(config_path, monkeypatch)
    monkeypatch.setattr(GitSync, "ensure_local_clone", lambda self: None)

    def fake_editor(template: str, editor: str | None = None) -> str:
        return (
            "---\n"
            "title: Mixed Tags\n"
            "last_edited: 2024-01-01T00:00:00+00:00\n"
            "date: 2024-01-01T00:00:00+00:00\n"
            "tags:\n"
            "  - til\n"
            "  - nope\n"
            "---\n\n"
            "Body.\n"
        )

    monkeypatch.setattr("terminotes.cli.open_editor", fake_editor)

    runner = CliRunner()
    result = runner.invoke(cli.cli, ["new"])

    assert result.exit_code == 0, result.output
    assert "Warning:" in result.output

    title, body, tags = _read_single_note(repo_dir / DB_FILENAME)
    assert title == "Mixed Tags"
    assert body == "Body."
    assert tags == ("til",)


def test_edit_command_with_unknown_tags_replaces_with_empty(
    tmp_path, monkeypatch
) -> None:
    config_path = _write_config(tmp_path)
    repo_dir = tmp_path / "notes-repo"
    _set_default_paths(config_path, monkeypatch)
    monkeypatch.setattr(GitSync, "ensure_local_clone", lambda self: None)

    storage = Storage(repo_dir / DB_FILENAME)
    storage.initialize()
    note = storage.create_note("Title", "Body", ["til"])

    def fake_editor(template: str, editor: str | None = None) -> str:
        return (
            "---\n"
            "title: Title\n"
            f"date: {note.created_at.isoformat()}\n"
            f"last_edited: {datetime.now().isoformat()}\n"
            "tags:\n"
            "  - not-allowed\n"
            "---\n\n"
            "Body updated.\n"
        )

    monkeypatch.setattr("terminotes.cli.open_editor", fake_editor)

    runner = CliRunner()
    result = runner.invoke(cli.cli, ["edit", str(note.id)])

    assert result.exit_code == 0, result.output
    assert "Warning:" in result.output

    conn = sqlite3.connect(repo_dir / DB_FILENAME)
    row = conn.execute(
        "SELECT tags FROM notes WHERE id = ?",
        (note.id,),
    ).fetchone()
    conn.close()

    assert row is not None
    assert tuple(json.loads(row[0])) == ()


def test_edit_command_with_mixed_tags_keeps_valid(tmp_path, monkeypatch) -> None:
    config_path = _write_config(tmp_path)
    repo_dir = tmp_path / "notes-repo"
    _set_default_paths(config_path, monkeypatch)
    monkeypatch.setattr(GitSync, "ensure_local_clone", lambda self: None)

    storage = Storage(repo_dir / DB_FILENAME)
    storage.initialize()
    note = storage.create_note("Title", "Body", ["til"])

    def fake_editor(template: str, editor: str | None = None) -> str:
        return (
            "---\n"
            "title: Title\n"
            f"date: {note.created_at.isoformat()}\n"
            f"last_edited: {datetime.now().isoformat()}\n"
            "tags:\n"
            "  - til\n"
            "  - not-allowed\n"
            "---\n\n"
            "Body updated.\n"
        )

    monkeypatch.setattr("terminotes.cli.open_editor", fake_editor)

    runner = CliRunner()
    result = runner.invoke(cli.cli, ["edit", str(note.id)])

    assert result.exit_code == 0, result.output
    assert "Warning:" in result.output

    conn = sqlite3.connect(repo_dir / DB_FILENAME)
    row = conn.execute(
        "SELECT tags FROM notes WHERE id = ?",
        (note.id,),
    ).fetchone()
    conn.close()

    assert row is not None
    assert tuple(json.loads(row[0])) == ("til",)


def test_info_command_displays_repo_and_config(tmp_path, monkeypatch, capsys) -> None:
    config_path = _write_config(tmp_path)
    repo_dir = tmp_path / "notes-repo"
    _set_default_paths(config_path, monkeypatch)
    monkeypatch.setattr(GitSync, "ensure_local_clone", lambda self: None)

    storage = Storage(repo_dir / DB_FILENAME)
    storage.initialize()
    storage.create_note("Info title", "Info body", ["til"])

    runner = CliRunner()
    result = runner.invoke(cli.cli, ["info"])

    assert result.exit_code == 0, result.output
    output = result.output
    assert "Database file" in output
    assert "Total notes" in output
    assert "Last edited" in output
    assert "git_remote_url" in output
