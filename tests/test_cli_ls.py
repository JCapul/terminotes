"""Tests for the 'tn ls' CLI subcommand."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
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
    # Avoid interacting with real git during CLI tests
    monkeypatch.setattr(GitSync, "ensure_local_clone", lambda self: None)
    monkeypatch.setattr(
        GitSync, "commit_db_update", lambda self, path, message=None: None
    )


def test_ls_lists_recent_notes_with_limit_and_reverse(
    tmp_path: Path, monkeypatch
) -> None:
    config_path = _write_config(tmp_path)
    repo_dir = tmp_path / "notes-repo"
    _set_default_paths(config_path, monkeypatch)

    storage = Storage(repo_dir / DB_FILENAME)
    storage.initialize()

    base = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    a = storage.create_note("Alpha", "", created_at=base, updated_at=base)
    storage.create_note(
        "Bravo",
        "",
        created_at=base + timedelta(minutes=1),
        updated_at=base + timedelta(minutes=1),
    )
    c = storage.create_note(
        "Charlie",
        "",
        created_at=base + timedelta(minutes=2),
        updated_at=base + timedelta(minutes=2),
    )
    # Make Alpha the most recently updated
    storage.update_note(a.id, "Alpha*", "", updated_at=base + timedelta(minutes=3))

    runner = CliRunner()
    result = runner.invoke(cli.cli, ["ls", "--limit", "2"])
    assert result.exit_code == 0, result.output
    lines = [line for line in result.output.strip().splitlines() if line.strip()]
    # Expect two lines: Alpha*, Charlie (by updated desc)
    assert len(lines) == 2
    assert str(a.id) in lines[0] and "Alpha*" in lines[0]
    assert str(c.id) in lines[1] and "Charlie" in lines[1]

    # Reverse order
    result_rev = runner.invoke(cli.cli, ["ls", "--limit", "2", "--reverse"])
    assert result_rev.exit_code == 0, result_rev.output
    lines_rev = [
        line for line in result_rev.output.strip().splitlines() if line.strip()
    ]
    assert len(lines_rev) == 2
    assert str(c.id) in lines_rev[0] and "Charlie" in lines_rev[0]
    assert str(a.id) in lines_rev[1] and "Alpha*" in lines_rev[1]


def test_ls_filters_by_tags(tmp_path: Path, monkeypatch) -> None:
    config_path = _write_config(tmp_path)
    repo_dir = tmp_path / "notes-repo"
    _set_default_paths(config_path, monkeypatch)

    storage = Storage(repo_dir / DB_FILENAME)
    storage.initialize()

    base = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    storage.create_note("Alpha", "", created_at=base, updated_at=base, tags=["work"])
    tagged = storage.create_note(
        "Bravo",
        "",
        created_at=base,
        updated_at=base,
        tags=["personal"],
    )

    runner = CliRunner()
    result = runner.invoke(cli.cli, ["ls", "--tag", "personal"])
    assert result.exit_code == 0, result.output

    lines = [line for line in result.output.splitlines() if line.strip()]
    assert len(lines) == 1
    assert str(tagged.id) in lines[0]
    assert "tags: personal" in lines[0]
