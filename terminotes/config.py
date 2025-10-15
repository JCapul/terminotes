"""Configuration management for Terminotes."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

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

    git_remote_url: str
    terminotes_dir: Path
    editor: str | None = None
    plugins: dict[str, dict[str, Any]] = field(default_factory=dict)
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

    if not isinstance(raw, dict):
        raise InvalidConfigError("Configuration root must be a TOML table")

    terminotes_section = raw.get("terminotes")
    if not isinstance(terminotes_section, dict):
        raise InvalidConfigError("'terminotes' section is required and must be a table")
    config_raw = terminotes_section

    base_dir = config_path.parent if path is not None else DEFAULT_CONFIG_DIR
    config_dir = base_dir.expanduser()

    # Allow users to override where the notes repository lives via
    # `terminotes_dir`. The path may be absolute or relative; relative paths
    # are resolved against the configuration directory.
    repo_path_raw = config_raw.get("terminotes_dir")
    if repo_path_raw is None:
        terminotes_dir = (config_dir / DEFAULT_REPO_DIRNAME).expanduser().resolve()
    elif isinstance(repo_path_raw, str):
        repo_path_str = repo_path_raw.strip()
        if repo_path_str:
            rp = Path(repo_path_str).expanduser()
            terminotes_dir = (rp if rp.is_absolute() else (config_dir / rp)).resolve()
        else:
            terminotes_dir = (config_dir / DEFAULT_REPO_DIRNAME).expanduser().resolve()
    else:
        raise InvalidConfigError("'terminotes_dir' must be a string when provided")

    git_remote_url_raw = config_raw.get("git_remote_url")
    if not isinstance(git_remote_url_raw, str):
        raise InvalidConfigError("'git_remote_url' is required and must be a string")
    git_remote_url = git_remote_url_raw.strip()
    if not git_remote_url:
        raise InvalidConfigError("'git_remote_url' must be a non-empty string")

    editor = config_raw.get("editor")
    if editor is not None and not isinstance(editor, str):
        raise InvalidConfigError("'editor' must be a string when provided")

    plugins_section = raw.get("plugins")
    plugins: dict[str, dict[str, Any]] = {}
    if isinstance(plugins_section, dict):
        for key, value in plugins_section.items():
            if not isinstance(key, str):  # pragma: no cover - defensive
                continue
            if isinstance(value, dict):
                plugins[key] = dict(value)
            else:
                plugins[key] = {}

    return TerminotesConfig(
        git_remote_url=git_remote_url,
        terminotes_dir=terminotes_dir,
        editor=editor,
        plugins=plugins,
        source_path=config_path,
    )


def bootstrap_config_file(path: Path) -> bool:
    """Create a default config file if missing.

    Returns True when the file was created, False if it already existed.
    """

    if path.exists():
        return False

    config_dir = path.parent
    config_dir.mkdir(parents=True, exist_ok=True)
    default_content = (
        "[terminotes]\n"
        'git_remote_url = "file:///path/to/notes.git"\n'
        'terminotes_dir = "notes-repo"\n'
        'editor = "vim"\n'
    )
    path.write_text(default_content, encoding="utf-8")
    return True
