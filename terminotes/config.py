"""Configuration management for Terminotes."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

DEFAULT_CONFIG_DIR = Path("~/.config/terminotes").expanduser()
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.toml"
DEFAULT_REPO_DIRNAME = "notes-repo"


class ConfigError(RuntimeError):
    """Base error for configuration related issues."""


class MissingConfigError(ConfigError):
    """Raised when the configuration file cannot be found."""

    def __init__(self, path: Path) -> None:
        super().__init__(f"Configuration file not found at {path}")
        self.path = path


class InvalidConfigError(ConfigError):
    """Raised when the configuration file misses required keys or values."""


@dataclass(slots=True)
class TerminotesConfig:
    """In-memory representation of the Terminotes configuration file."""

    notes_repo_url: str
    notes_repo_path: Path
    allowed_tags: tuple[str, ...]
    editor: str | None = None
    source_path: Path | None = None


def load_config(path: Path | None = None) -> TerminotesConfig:
    """Load configuration from ``path`` or the default location.

    Parameters
    ----------
    path:
        Optional location of the configuration file. When ``None`` the default
        path (``~/.config/terminotes/config.toml``) is used.

    Raises
    ------
    MissingConfigError
        If the file cannot be found.
    InvalidConfigError
        If mandatory settings are missing or malformed.
    """

    config_path = (path or DEFAULT_CONFIG_PATH).expanduser()
    if not config_path.exists():
        raise MissingConfigError(config_path)

    with config_path.open("rb") as fh:
        raw = tomllib.load(fh)

    base_dir = config_path.parent if path is not None else DEFAULT_CONFIG_DIR
    config_dir = base_dir.expanduser()

    # Allow users to override where the notes repository lives via
    # `notes_repo_path`. The path may be absolute or relative; relative paths
    # are resolved against the configuration directory.
    repo_path_raw = raw.get("notes_repo_path")
    if repo_path_raw is None:
        notes_repo_path = (config_dir / DEFAULT_REPO_DIRNAME).expanduser().resolve()
    elif isinstance(repo_path_raw, str):
        repo_path_str = repo_path_raw.strip()
        if repo_path_str:
            rp = Path(repo_path_str).expanduser()
            notes_repo_path = (rp if rp.is_absolute() else (config_dir / rp)).resolve()
        else:
            notes_repo_path = (config_dir / DEFAULT_REPO_DIRNAME).expanduser().resolve()
    else:
        raise InvalidConfigError("'notes_repo_path' must be a string when provided")

    notes_repo_url_raw = raw.get("notes_repo_url")
    if not isinstance(notes_repo_url_raw, str):
        raise InvalidConfigError("'notes_repo_url' is required and must be a string")
    notes_repo_url = notes_repo_url_raw.strip()
    if not notes_repo_url:
        raise InvalidConfigError("'notes_repo_url' must be a non-empty string")

    allowed_tags_raw: Sequence[str] | None = raw.get("allowed_tags")
    if allowed_tags_raw is None:
        allowed_tags: tuple[str, ...] = ()
    else:
        if not isinstance(allowed_tags_raw, Sequence) or isinstance(
            allowed_tags_raw, (str, bytes)
        ):
            raise InvalidConfigError("'allowed_tags' must be a list of strings")
        cleaned: list[str] = []
        for tag in allowed_tags_raw:
            if not isinstance(tag, str):
                raise InvalidConfigError(
                    "All entries in 'allowed_tags' must be strings"
                )
            tag_clean = tag.strip()
            if not tag_clean:
                raise InvalidConfigError("Tags cannot be empty strings")
            cleaned.append(tag_clean)
        allowed_tags = tuple(cleaned)

    editor = raw.get("editor")
    if editor is not None and not isinstance(editor, str):
        raise InvalidConfigError("'editor' must be a string when provided")

    return TerminotesConfig(
        notes_repo_url=notes_repo_url,
        notes_repo_path=notes_repo_path,
        allowed_tags=allowed_tags,
        editor=editor,
        source_path=config_path,
    )


def ensure_tags_known(config: TerminotesConfig, tags: Iterable[str]) -> None:
    """Validate that each tag is present in ``config.allowed_tags``.

    Raises
    ------
    InvalidConfigError
        If tags contain unknown values.
    """

    allowed = set(config.allowed_tags)
    unknown = [tag for tag in tags if tag not in allowed]
    if unknown:
        tag_list = ", ".join(sorted(unknown))
        raise InvalidConfigError(f"Unknown tag(s): {tag_list}")
