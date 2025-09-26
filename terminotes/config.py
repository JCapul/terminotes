"""Configuration management for Terminotes."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

DEFAULT_CONFIG_DIR = Path("~/.config/terminotes").expanduser()
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.toml"
DEFAULT_REPO_DIRNAME = "notes-repo"
TEMPLATE_PACKAGE = "terminotes.templates.export.html"
TEMPLATE_RELATIVE_DIR = Path("templates") / "export" / "html"
TEMPLATE_FILES = ("index.html", "note.html", "styles.css", "search.js")


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
    # `terminotes_dir`. The path may be absolute or relative; relative paths
    # are resolved against the configuration directory.
    repo_path_raw = raw.get("terminotes_dir")
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

    git_remote_url_raw = raw.get("git_remote_url")
    if not isinstance(git_remote_url_raw, str):
        raise InvalidConfigError("'git_remote_url' is required and must be a string")
    git_remote_url = git_remote_url_raw.strip()
    if not git_remote_url:
        raise InvalidConfigError("'git_remote_url' must be a non-empty string")

    editor = raw.get("editor")
    if editor is not None and not isinstance(editor, str):
        raise InvalidConfigError("'editor' must be a string when provided")

    ensure_export_templates(config_dir)

    return TerminotesConfig(
        git_remote_url=git_remote_url,
        terminotes_dir=terminotes_dir,
        editor=editor,
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
        'git_remote_url = "file:///path/to/notes.git"\n'
        'terminotes_dir = "notes-repo"\n'
        'editor = "vim"\n'
    )
    path.write_text(default_content, encoding="utf-8")
    ensure_export_templates(config_dir)
    return True


def ensure_export_templates(config_dir: Path) -> None:
    """Ensure default export templates exist under the configuration directory."""

    target_dir = config_dir / TEMPLATE_RELATIVE_DIR
    for filename in TEMPLATE_FILES:
        target_path = target_dir / filename
        if target_path.exists():
            continue
        target_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = (
                resources.files(TEMPLATE_PACKAGE).joinpath(filename).read_text("utf-8")
            )
        except FileNotFoundError:  # pragma: no cover - defensive
            continue
        target_path.write_text(data, encoding="utf-8")
