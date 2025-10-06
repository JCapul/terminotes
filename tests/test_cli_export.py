"""CLI tests for the 'tn export' command."""

from __future__ import annotations

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
    monkeypatch.setattr(GitSync, "ensure_local_clone", lambda self: None)
    monkeypatch.setattr(
        GitSync, "commit_db_update", lambda self, path, message=None: None
    )


def _seed_notes(repo_dir: Path) -> None:
    storage = Storage(repo_dir / DB_FILENAME)
    storage.initialize()
    storage.create_note("Exported", "Body text", description="desc", can_publish=True)
    storage.create_note("Second", "Another body", tags=["work"])


def test_export_html_creates_static_site(tmp_path: Path, monkeypatch) -> None:
    config_path = _write_config(tmp_path)
    repo_dir = tmp_path / "notes-repo"
    _set_default_paths(config_path, monkeypatch)

    _seed_notes(repo_dir)

    runner = CliRunner()
    output_dir = tmp_path / "site"
    result = runner.invoke(
        cli.cli,
        [
            "export",
            "--format",
            "html",
            "--dest",
            str(output_dir),
            "--site-title",
            "My Site",
        ],
    )

    assert result.exit_code == 0, result.output
    index_html = output_dir / "index.html"
    assert index_html.exists()
    assert "My Site" in index_html.read_text(encoding="utf-8")
    assert (output_dir / "notes-data.json").exists()
    assert any((output_dir / "notes").glob("*.html"))


def test_export_markdown_writes_files(tmp_path: Path, monkeypatch) -> None:
    config_path = _write_config(tmp_path)
    repo_dir = tmp_path / "notes-repo"
    _set_default_paths(config_path, monkeypatch)

    _seed_notes(repo_dir)

    runner = CliRunner()
    output_dir = tmp_path / "md"
    result = runner.invoke(
        cli.cli,
        ["export", "-f", "markdown", "-d", str(output_dir)],
    )

    assert result.exit_code == 0, result.output
    md_files = list(output_dir.glob("*.md"))
    assert md_files
    content = md_files[0].read_text(encoding="utf-8")
    assert content.startswith("---")
    assert "Body text" in content or "Another body" in content


def test_export_help_short_flag(monkeypatch) -> None:
    monkeypatch.setattr(GitSync, "ensure_local_clone", lambda self: None)
    runner = CliRunner()

    result = runner.invoke(cli.cli, ["export", "-h"])

    assert result.exit_code == 0
    assert "Usage" in result.output
