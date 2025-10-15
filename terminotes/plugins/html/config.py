"""Configuration helpers for the built-in HTML exporter plugin."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING

from terminotes.config import DEFAULT_CONFIG_DIR, TerminotesConfig

PLUGIN_ID = "terminotes-html-plugin"

TEMPLATE_PACKAGE = "terminotes.plugins.html.templates"
TEMPLATE_RELATIVE_DIR = Path(PLUGIN_ID) / "templates"
TEMPLATE_FILES = ("index.html", "note.html", "styles.css", "search.js")

if TYPE_CHECKING:
    from terminotes.config import TerminotesConfig
DEFAULT_SITE_TITLE = "Terminotes"


@dataclass(frozen=True)
class HtmlPluginConfig:
    """Resolved configuration data for the HTML exporter plugin."""

    site_title: str
    templates_root: Path


def ensure_templates(config_dir: Path) -> None:
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


def resolve_plugin_config(config: "TerminotesConfig") -> HtmlPluginConfig:
    """Convert configuration data into plugin configuration."""

    config_dir = (
        config.source_path.parent
        if config.source_path is not None
        else DEFAULT_CONFIG_DIR
    )

    raw_settings = config.plugins.get(PLUGIN_ID, {})

    site_title_raw = raw_settings.get("site_title", DEFAULT_SITE_TITLE)
    site_title = str(site_title_raw).strip() or DEFAULT_SITE_TITLE

    templates_root_raw = raw_settings.get("templates_root")
    if templates_root_raw is None:
        templates_root = config_dir
    else:
        root_path = Path(str(templates_root_raw)).expanduser()
        if not root_path.is_absolute():
            root_path = (config_dir / root_path).resolve()
        templates_root = root_path

    return HtmlPluginConfig(site_title=site_title, templates_root=templates_root)


def templates_dir_from(config: HtmlPluginConfig) -> Path:
    """Return the full template directory path for the given configuration."""

    return config.templates_root / TEMPLATE_RELATIVE_DIR


__all__ = [
    "DEFAULT_SITE_TITLE",
    "PLUGIN_ID",
    "HtmlPluginConfig",
    "ensure_templates",
    "resolve_plugin_config",
    "templates_dir_from",
]
