"""Tests for the 'tn search' CLI subcommand."""

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


def test_search_prints_matches_with_limit_and_reverse(
    tmp_path: Path, monkeypatch
) -> None:
    config_path = _write_config(tmp_path)
    repo_dir = tmp_path / "notes-repo"
    _set_default_paths(config_path, monkeypatch)

    storage = Storage(repo_dir / DB_FILENAME)
    storage.initialize()

    base = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    storage.create_note("Alpha", "needle here", created_at=base, updated_at=base)
    b = storage.create_note(
        "Needle in title",
        "",
        created_at=base,
        updated_at=base + timedelta(minutes=1),
    )
    storage.create_note(
        "Gamma",
        "no match",
        created_at=base,
        updated_at=base + timedelta(minutes=2),
    )
    d = storage.create_note(
        "Delta",
        "another needle spotted",
        created_at=base,
        updated_at=base + timedelta(minutes=3),
    )

    runner = CliRunner()
    result = runner.invoke(cli.cli, ["search", "needle", "--limit", "2"])
    assert result.exit_code == 0, result.output
    lines = [line for line in result.output.strip().splitlines() if line.strip()]
    # Matching order: d, b, a; with limit 2 -> d, b
    assert len(lines) == 2
    assert str(d.id) in lines[0]
    assert str(b.id) in lines[1]

    # Reverse order with same limit -> b, d
    result_rev = runner.invoke(
        cli.cli, ["search", "needle", "--limit", "2", "--reverse"]
    )
    assert result_rev.exit_code == 0, result_rev.output
    lines_rev = [
        line for line in result_rev.output.strip().splitlines() if line.strip()
    ]
    assert len(lines_rev) == 2
    assert str(b.id) in lines_rev[0]
    assert str(d.id) in lines_rev[1]


def test_search_empty_pattern_errors(tmp_path: Path, monkeypatch) -> None:
    config_path = _write_config(tmp_path)
    _set_default_paths(config_path, monkeypatch)

    runner = CliRunner()
    # Click passes empty string argument when quoted; ensure we error out
    result = runner.invoke(cli.cli, ["search", ""])  # empty pattern
    assert result.exit_code == 1
    assert "must not be empty" in result.output.lower()


def test_search_no_results_prints_nothing(tmp_path: Path, monkeypatch) -> None:
    config_path = _write_config(tmp_path)
    repo_dir = tmp_path / "notes-repo"
    _set_default_paths(config_path, monkeypatch)

    storage = Storage(repo_dir / DB_FILENAME)
    storage.initialize()
    storage.create_note("Alpha", "body")

    runner = CliRunner()
    result = runner.invoke(cli.cli, ["search", "nomatch"])
    assert result.exit_code == 0, result.output
    assert result.output.strip() == ""


def test_search_filters_by_tags(tmp_path: Path, monkeypatch) -> None:
    config_path = _write_config(tmp_path)
    repo_dir = tmp_path / "notes-repo"
    _set_default_paths(config_path, monkeypatch)

    storage = Storage(repo_dir / DB_FILENAME)
    storage.initialize()

    base = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    storage.create_note(
        "Alpha",
        "needle here",
        created_at=base,
        updated_at=base,
        tags=["work"],
    )
    tagged = storage.create_note(
        "Beta",
        "needle again",
        created_at=base,
        updated_at=base,
        tags=["personal"],
    )

    runner = CliRunner()
    result = runner.invoke(cli.cli, ["search", "needle", "--tag", "personal"])
    assert result.exit_code == 0, result.output
    lines = [line for line in result.output.splitlines() if line.strip()]
    assert len(lines) == 1
    assert str(tagged.id) in lines[0]
    assert "tags: personal" in lines[0]
