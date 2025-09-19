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
    config_file.write_text(textwrap.dedent(content), encoding="utf-8")
    return config_file


def test_load_config_success(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        """
        notes_repo_url = "git@example:notes.git"
        notes_repo_path = "~/notes"
        allowed_tags = ["python", "til"]
        editor = "nvim"
        """,
    )

    config = load_config(config_path)
    assert isinstance(config, TerminotesConfig)
    assert config.notes_repo_url == "git@example:notes.git"
    assert config.notes_repo_path == Path("~/notes")
    assert config.allowed_tags == ("python", "til")
    assert config.editor == "nvim"


def test_load_config_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing.toml"
    with pytest.raises(ConfigError):
        load_config(missing)


def test_load_config_rejects_empty_tags(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        """
        notes_repo_url = "git@example:notes.git"
        notes_repo_path = "~/notes"
        allowed_tags = ["python", "  "]
        """,
    )

    with pytest.raises(InvalidConfigError):
        load_config(config_path)


def test_ensure_tags_known_rejects_unknown(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        """
        notes_repo_url = "git@example:notes.git"
        notes_repo_path = "~/notes"
        allowed_tags = ["python"]
        """,
    )
    config = load_config(config_path)

    with pytest.raises(InvalidConfigError):
        ensure_tags_known(config, ["til"])


def test_ensure_tags_known_accepts_subset(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        """
        notes_repo_url = "git@example:notes.git"
        notes_repo_path = "~/notes"
        allowed_tags = ["python", "til"]
        """,
    )
    config = load_config(config_path)

    ensure_tags_known(config, ["python"])
