from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
from terminotes.config import (
    ConfigError,
    InvalidConfigError,
    TerminotesConfig,
    ensure_tags_known,
    load_config,
)


def write_config(tmp_path: Path, content: str) -> Path:
    config_file = tmp_path / "config.toml"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text(textwrap.dedent(content), encoding="utf-8")
    return config_file


def test_notes_repo_path_defaults_to_config_dir(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path / "nested",
        """
        allowed_tags = []
        notes_repo_url = "git@example:notes.git"
        """,
    )

    config = load_config(config_path)
    assert config.notes_repo_path.parent == (config_path.parent).expanduser().resolve()
    assert config.source_path == config_path


def test_load_config_success(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        """
        allowed_tags = ["python", "til"]
        editor = "nvim"
        notes_repo_url = "git@example:notes.git"
        """,
    )

    config = load_config(config_path)
    assert isinstance(config, TerminotesConfig)
    assert config.notes_repo_url == "git@example:notes.git"
    assert config.notes_repo_path.name == "notes-repo"
    assert config.allowed_tags == ("python", "til")
    assert config.editor == "nvim"
    assert config.source_path == config_path


def test_load_config_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing.toml"
    with pytest.raises(ConfigError):
        load_config(missing)


def test_load_config_rejects_empty_tags(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        """
        allowed_tags = ["python", "  "]
        notes_repo_url = "git@example:notes.git"
        """,
    )

    with pytest.raises(InvalidConfigError):
        load_config(config_path)


def test_ensure_tags_known_rejects_unknown(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        """
        allowed_tags = ["python"]
        notes_repo_url = "git@example:notes.git"
        """,
    )
    config = load_config(config_path)

    with pytest.raises(InvalidConfigError):
        ensure_tags_known(config, ["til"])


def test_ensure_tags_known_accepts_subset(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        """
        allowed_tags = ["python", "til"]
        notes_repo_url = "git@example:notes.git"
        """,
    )
    config = load_config(config_path)

    ensure_tags_known(config, ["python"])


def test_notes_repo_url_is_required(tmp_path: Path) -> None:
    # Missing key
    config_path = write_config(
        tmp_path,
        """
        allowed_tags = []
        """,
    )
    with pytest.raises(InvalidConfigError):
        load_config(config_path)

    # Empty string
    config_path = write_config(
        tmp_path,
        """
        allowed_tags = []
        notes_repo_url = "  "
        """,
    )
    with pytest.raises(InvalidConfigError):
        load_config(config_path)
