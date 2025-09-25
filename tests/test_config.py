from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
from terminotes.config import (
    ConfigError,
    InvalidConfigError,
    TerminotesConfig,
    load_config,
)


def write_config(tmp_path: Path, content: str) -> Path:
    config_file = tmp_path / "config.toml"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text(textwrap.dedent(content), encoding="utf-8")
    return config_file


def test_terminotes_dir_defaults_to_config_dir(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path / "nested",
        """
        git_remote_url = "git@example:notes.git"
        """,
    )

    config = load_config(config_path)
    assert config.terminotes_dir.parent == (config_path.parent).expanduser().resolve()
    assert config.source_path == config_path


def test_load_config_success(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        """
        editor = "nvim"
        git_remote_url = "git@example:notes.git"
        """,
    )

    config = load_config(config_path)
    assert isinstance(config, TerminotesConfig)
    assert config.git_remote_url == "git@example:notes.git"
    assert config.terminotes_dir.name == "notes-repo"
    assert config.editor == "nvim"
    assert config.source_path == config_path


def test_load_config_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing.toml"
    with pytest.raises(ConfigError):
        load_config(missing)


def test_git_remote_url_is_required(tmp_path: Path) -> None:
    # Missing key
    config_path = write_config(
        tmp_path,
        """
        """,
    )
    with pytest.raises(InvalidConfigError):
        load_config(config_path)

    # Empty string
    config_path = write_config(
        tmp_path,
        """
        git_remote_url = "  "
        """,
    )
    with pytest.raises(InvalidConfigError):
        load_config(config_path)
