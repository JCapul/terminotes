"""Configuration management for Terminotes."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

CONFIG_FILENAMES = (
    "config.toml",
    "terminotes.toml",
)

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
class BackupConfig:
    """Settings for a backup mechanism."""

    enabled: bool
    kind: str
    repo_url: str | None = None


@dataclass(slots=True)
class TerminotesConfig:
    """In-memory representation of the Terminotes configuration file."""

    repo_path: Path
    allowed_tags: tuple[str, ...]
    editor: str | None = None
    backup: BackupConfig | None = None
    source_path: Path | None = None

    @property
    def normalized_repo_path(self) -> Path:
        """Return the expanded repository path."""
        return self.repo_path


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
    notes_repo_path = (config_dir / DEFAULT_REPO_DIRNAME).expanduser().resolve()

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

    backup_raw = raw.get("backup")
    backup: BackupConfig | None
    if backup_raw is None:
        backup = None
    else:
        if not isinstance(backup_raw, dict):
            raise InvalidConfigError("'backup' must be a table of settings")

        enabled = bool(backup_raw.get("enabled", True))
        kind = backup_raw.get("type", "git")
        if not isinstance(kind, str) or not kind.strip():
            raise InvalidConfigError("'backup.type' must be a non-empty string")
        kind = kind.strip()

        repo_url_raw = backup_raw.get("repo_url")
        repo_url: str | None
        if repo_url_raw is None:
            repo_url = None
        elif isinstance(repo_url_raw, str):
            repo_url = repo_url_raw.strip() or None
        else:
            raise InvalidConfigError("'backup.repo_url' must be a string when provided")

        if enabled and kind == "git" and not repo_url:
            raise InvalidConfigError("'backup.repo_url' must be set when using git backup")

        backup = BackupConfig(enabled=enabled, kind=kind, repo_url=repo_url)

    return TerminotesConfig(
        repo_path=notes_repo_path,
        allowed_tags=allowed_tags,
        editor=editor,
        backup=backup,
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
