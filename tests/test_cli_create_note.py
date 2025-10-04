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
from terminotes.notes_frontmatter import (
    FRONTMATTER_DELIM,
    parse_document,
    render_document,
)
from terminotes.storage import DB_FILENAME, Storage


def _write_config(base_dir: Path, *, git_enabled: bool = True) -> Path:
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


def _read_single_note_timestamps(db_path: Path) -> tuple[datetime, datetime]:
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT created_at, updated_at FROM notes").fetchone()
    conn.close()
    assert row is not None
    return datetime.fromisoformat(row[0]), datetime.fromisoformat(row[1])


def _load_metadata_from_template(template: str) -> dict[str, object]:
    prefix = f"{FRONTMATTER_DELIM}\n"
    suffix = f"\n{FRONTMATTER_DELIM}"
    _, remainder = template.split(prefix, 1)
    block, _ = remainder.split(suffix, 1)
    data = yaml.safe_load(block) or {}
    assert isinstance(data, dict)
    return data


def test_new_command_creates_note_with_metadata(tmp_path, monkeypatch) -> None:
    config_path = _write_config(tmp_path)
    repo_dir = tmp_path / "notes-repo"
    _set_default_paths(config_path, monkeypatch)
    monkeypatch.setattr(GitSync, "ensure_local_clone", lambda self: None)

    captured_template: dict[str, str] = {}

    def fake_editor(template: str, editor: str | None = None) -> str:
        captured_template["value"] = template
        return (
            f"{FRONTMATTER_DELIM}\n"
            "title: Captured Title\n"
            'date: "2024-01-01T12:00:00+00:00"\n'
            'last_edited: "2024-01-01T12:00:00+00:00"\n'
            "tags:\n"
            "  - Work\n"
            "  - Focus\n"
            f"{FRONTMATTER_DELIM}\n\n"
            "Body from editor. #til #python\n"
        )

    monkeypatch.setattr("terminotes.cli.open_editor", fake_editor)

    runner = CliRunner()
    result = runner.invoke(cli.cli, ["edit"])

    assert result.exit_code == 0, result.output

    template = captured_template["value"]
    metadata = _load_metadata_from_template(template)
    assert "date" in metadata
    assert "last_edited" in metadata
    assert metadata.get("tags") == []

    title, body = _read_single_note(repo_dir / DB_FILENAME)
    assert title == "Captured Title"
    assert body == "Body from editor. #til #python"

    storage = Storage(repo_dir / DB_FILENAME)
    storage.initialize()
    stored_note = storage.fetch_note(1)
    assert sorted(tag.name for tag in stored_note.tags) == ["focus", "work"]


def test_new_command_respects_custom_timestamps(tmp_path, monkeypatch) -> None:
    config_path = _write_config(tmp_path)
    repo_dir = tmp_path / "notes-repo"
    _set_default_paths(config_path, monkeypatch)
    monkeypatch.setattr(GitSync, "ensure_local_clone", lambda self: None)

    created = "2023-01-01T00:00:00+00:00"
    updated = "2023-02-02T10:00:00+00:00"

    def fake_editor(template: str, editor: str | None = None) -> str:
        return (
            f"{FRONTMATTER_DELIM}\n"
            "title: Has Timestamps\n"
            f'date: "{created}"\n'
            f'last_edited: "{updated}"\n'
            f"{FRONTMATTER_DELIM}\n\n"
            "Body.\n"
        )

    monkeypatch.setattr("terminotes.cli.open_editor", fake_editor)

    runner = CliRunner()
    result = runner.invoke(cli.cli, ["edit"])
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
    extra_payload = {
        "link": {
            "source_url": "https://example.com",
            "wayback": "https://web.archive.org/example",
        }
    }
    note = storage.create_note(
        "Existing Title", "Body", tags=["initial"], extra_data=extra_payload
    )

    captured_template: dict[str, str] = {}

    def fake_editor(template: str, editor: str | None = None) -> str:
        captured_template["value"] = template
        updated_wayback = "https://web.archive.org/example-updated"
        return (
            f"{FRONTMATTER_DELIM}\n"
            "title: Updated Title\n"
            f'date: "{note.created_at.isoformat()}"\n'
            f'last_edited: "{datetime.now().isoformat()}"\n'
            "tags:\n"
            "  - Updated\n"
            "  - Focus\n"
            "extra_data:\n"
            "  link:\n"
            "    source_url: https://example.com\n"
            f"    wayback: {updated_wayback}\n"
            f"{FRONTMATTER_DELIM}\n\n"
            "Updated body. #python\n"
        )

    monkeypatch.setattr("terminotes.cli.open_editor", fake_editor)

    runner = CliRunner()
    result = runner.invoke(cli.cli, ["edit", "--id", str(note.id)])

    assert result.exit_code == 0, result.output

    template = captured_template["value"]
    metadata = _load_metadata_from_template(template)
    assert metadata["title"] == "Existing Title"
    assert "last_edited" in metadata
    assert metadata.get("tags") == ["initial"]
    assert metadata.get("extra_data") == extra_payload

    title, body = _read_single_note(repo_dir / DB_FILENAME)
    assert title == "Updated Title"
    assert body == "Updated body. #python"

    updated_note = storage.fetch_note(note.id)
    assert sorted(tag.name for tag in updated_note.tags) == ["focus", "updated"]
    assert updated_note.extra_data is not None
    assert json.loads(updated_note.extra_data) == {
        "link": {
            "source_url": "https://example.com",
            "wayback": "https://web.archive.org/example-updated",
        }
    }


def test_edit_command_auto_updates_last_edited_when_metadata_unchanged(
    tmp_path, monkeypatch
) -> None:
    config_path = _write_config(tmp_path)
    repo_dir = tmp_path / "notes-repo"
    _set_default_paths(config_path, monkeypatch)
    monkeypatch.setattr(GitSync, "ensure_local_clone", lambda self: None)

    storage = Storage(repo_dir / DB_FILENAME)
    storage.initialize()
    note = storage.create_note("Title", "Body")
    original_updated_at = note.updated_at

    def fake_editor(template: str, editor: str | None = None) -> str:
        parsed = parse_document(template)
        return render_document(
            title=parsed.title or "",
            body="Updated body without touching metadata.",
            metadata=parsed.metadata,
        )

    monkeypatch.setattr("terminotes.cli.open_editor", fake_editor)

    runner = CliRunner()
    result = runner.invoke(cli.cli, ["edit", "--id", str(note.id)])
    assert result.exit_code == 0, result.output

    updated_note = storage.fetch_note(note.id)
    assert updated_note.body == "Updated body without touching metadata."
    assert updated_note.updated_at > original_updated_at


def test_edit_command_allows_changing_timestamps(tmp_path, monkeypatch) -> None:
    config_path = _write_config(tmp_path)
    repo_dir = tmp_path / "notes-repo"
    _set_default_paths(config_path, monkeypatch)
    monkeypatch.setattr(GitSync, "ensure_local_clone", lambda self: None)

    storage = Storage(repo_dir / DB_FILENAME)
    storage.initialize()
    note = storage.create_note("Title", "Body")

    new_created = "2020-05-05T05:05:05+00:00"
    new_updated = "2021-06-06T06:06:06+00:00"

    def fake_editor(template: str, editor: str | None = None) -> str:
        return (
            f"{FRONTMATTER_DELIM}\n"
            "title: Title\n"
            f'date: "{new_created}"\n'
            f'last_edited: "{new_updated}"\n'
            f"{FRONTMATTER_DELIM}\n\n"
            "Body updated. #til\n"
        )

    monkeypatch.setattr("terminotes.cli.open_editor", fake_editor)

    runner = CliRunner()
    result = runner.invoke(cli.cli, ["edit", "--id", str(note.id)])
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


def test_edit_with_last_option_edits_last_updated(tmp_path, monkeypatch) -> None:
    config_path = _write_config(tmp_path)
    repo_dir = tmp_path / "notes-repo"
    _set_default_paths(config_path, monkeypatch)
    monkeypatch.setattr(GitSync, "ensure_local_clone", lambda self: None)

    storage = Storage(repo_dir / DB_FILENAME)
    storage.initialize()
    first = storage.create_note("First title", "First body")
    storage.create_note("Second title", "Second body")

    # Update first note to ensure it becomes the most recently edited entry.
    storage.update_note(first.id, "First title", "First body updated")

    captured_template: dict[str, str] = {}

    def fake_editor(template: str, editor: str | None = None) -> str:
        captured_template["value"] = template
        return (
            f"{FRONTMATTER_DELIM}\n"
            "title: First title updated\n"
            f'date: "{first.created_at.isoformat()}"\n'
            f'last_edited: "{datetime.now().isoformat()}"\n'
            f"{FRONTMATTER_DELIM}\n\n"
            "First body updated via edit. #python\n"
        )

    monkeypatch.setattr("terminotes.cli.open_editor", fake_editor)

    runner = CliRunner()
    result = runner.invoke(cli.cli, ["edit", "--last"])

    assert result.exit_code == 0, result.output

    template = captured_template["value"]
    metadata = _load_metadata_from_template(template)
    assert metadata["title"] == "First title"

    conn = sqlite3.connect(repo_dir / DB_FILENAME)
    row = conn.execute(
        "SELECT title, body FROM notes WHERE id = ?",
        (first.id,),
    ).fetchone()
    conn.close()

    assert row is not None
    assert row[0] == "First title updated"
    assert row[1] == "First body updated via edit. #python"


## Behavior change: without --id, a new note is created instead of editing last updated.


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


def test_info_command_displays_repo_and_config(tmp_path, monkeypatch, capsys) -> None:
    config_path = _write_config(tmp_path)
    repo_dir = tmp_path / "notes-repo"
    _set_default_paths(config_path, monkeypatch)
    monkeypatch.setattr(GitSync, "ensure_local_clone", lambda self: None)

    storage = Storage(repo_dir / DB_FILENAME)
    storage.initialize()
    storage.create_note("Info title", "Info body", tags=["beta", "alpha"])

    runner = CliRunner()
    result = runner.invoke(cli.cli, ["info"])

    assert result.exit_code == 0, result.output
    output = result.output
    assert "Database file" in output
    assert "Total notes" in output
    assert "Tags          : alpha, beta" in output
    assert "Last edited" in output
    assert "git_remote_url" in output


def test_info_command_shows_none_when_no_tags(tmp_path, monkeypatch) -> None:
    config_path = _write_config(tmp_path)
    repo_dir = tmp_path / "notes-repo"
    _set_default_paths(config_path, monkeypatch)
    monkeypatch.setattr(GitSync, "ensure_local_clone", lambda self: None)

    storage = Storage(repo_dir / DB_FILENAME)
    storage.initialize()

    runner = CliRunner()
    result = runner.invoke(cli.cli, ["info"])

    assert result.exit_code == 0, result.output
    output = result.output
    assert "Tags          : (none)" in output
