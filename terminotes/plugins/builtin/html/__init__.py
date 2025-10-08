"""Built-in HTML exporter plugin for Terminotes."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape
from importlib import resources
from pathlib import Path
from typing import Any, Mapping

from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape
from markupsafe import Markup

from ....config import (
    DEFAULT_CONFIG_DIR,
    TEMPLATE_FILES,
    TEMPLATE_PACKAGE,
    TEMPLATE_RELATIVE_DIR,
)
from ....exporters import ExportError
from ....plugins import BootstrapContext, ExportContribution, hookimpl
from ....storage import NoteSnapshot, Storage

PLUGIN_ID = "terminotes-builtin-html"
_DEFAULT_SITE_TITLE = "Terminotes"


@dataclass(frozen=True)
class HtmlPluginConfig:
    """Resolved configuration data for the HTML exporter plugin."""

    site_title: str
    templates_root: Path


_current_config = HtmlPluginConfig(
    site_title=_DEFAULT_SITE_TITLE,
    templates_root=DEFAULT_CONFIG_DIR,
)


def _render_body_html(body: str) -> Markup:
    paragraphs = [segment.strip() for segment in body.split("\n\n") if segment.strip()]
    if not paragraphs:
        return Markup("<p>(No content)</p>")
    html_parts: list[str] = []
    for para in paragraphs:
        escaped = escape(para).replace("\n", "<br />")
        html_parts.append(f"<p>{escaped}</p>")
    return Markup("\n".join(html_parts))


def _slugify(value: str) -> str:
    value = value.strip().lower()
    if not value:
        return "note"
    slug = re.sub(r"[^a-z0-9]+", "-", value)
    slug = slug.strip("-")
    return slug or "note"


class HtmlExporter:
    """Render notes into a static HTML site with client-side search."""

    def __init__(self, templates_dir: Path, *, site_title: str) -> None:
        self.templates_dir = templates_dir
        self.site_title = site_title or _DEFAULT_SITE_TITLE
        self._env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def export(self, notes: list[NoteSnapshot], destination: Path) -> int:
        dest = destination
        dest.mkdir(parents=True, exist_ok=True)

        try:
            index_template = self._env.get_template("index.html")
            note_template = self._env.get_template("note.html")
        except TemplateNotFound as exc:  # pragma: no cover - template existence tested
            raise ExportError(
                f"Template '{exc.name}' not found in {self.templates_dir}"
            ) from exc

        styles_template = self._read_asset("styles.css")
        search_js_template = self._read_asset("search.js")

        (dest / "styles.css").write_text(styles_template, encoding="utf-8")
        (dest / "search.js").write_text(search_js_template, encoding="utf-8")

        notes_dir = dest / "notes"
        notes_dir.mkdir(exist_ok=True)

        notes_listing: list[dict[str, object]] = []
        notes_data: list[dict[str, object]] = []

        count = 0
        for note in notes:
            count += 1
            slug = _slugify(note.title or f"note-{note.id}")
            filename = f"note-{note.id}-{slug}.html"
            note_path = notes_dir / filename
            url = f"notes/{filename}"

            tags_display = ", ".join(note.tags) if note.tags else "–"
            body_html = _render_body_html(note.body or "")

            note_title = note.title or f"Note {note.id}"
            created_pretty = note.created_at.isoformat(" ", "seconds")
            updated_pretty = note.updated_at.isoformat(" ", "seconds")

            note_markup = note_template.render(
                title=note_title,
                created_at=created_pretty,
                created_at_iso=note.created_at.isoformat(),
                updated_at=updated_pretty,
                updated_at_iso=note.updated_at.isoformat(),
                tags=tags_display,
                body_html=body_html,
            )
            note_path.write_text(note_markup, encoding="utf-8")

            summary_source = note.description or note.body
            summary = (summary_source or "").strip().splitlines()
            summary_text = summary[0] if summary else ""
            summary_text = summary_text[:200] + ("…" if len(summary_text) > 200 else "")

            summary_display = summary_text or "(No summary)"
            notes_listing.append(
                {
                    "title": note_title or "Untitled note",
                    "url": url,
                    "updated": updated_pretty,
                    "tags_display": tags_display,
                    "summary": summary_display,
                    "extra_data": note.extra_data,
                }
            )

            notes_data.append(
                {
                    "id": note.id,
                    "title": note.title,
                    "description": note.description,
                    "body": note.body,
                    "created_at": note.created_at.isoformat(),
                    "updated_at": note.updated_at.isoformat(),
                    "tags": note.tags,
                    "url": url,
                    "summary": summary_text,
                    "extra_data": note.extra_data,
                }
            )

        notes_json_path = dest / "notes-data.json"
        notes_json_path.write_text(json.dumps(notes_data, indent=2), encoding="utf-8")

        generated_stamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        rendered_index = index_template.render(
            site_title=self.site_title,
            notes_count=count,
            generated_at=generated_stamp,
            notes=notes_listing,
        )
        (dest / "index.html").write_text(rendered_index, encoding="utf-8")

        return count

    def _read_asset(self, name: str) -> str:
        template_path = self.templates_dir / name
        if not template_path.exists():
            raise ExportError(f"Template '{name}' not found in {self.templates_dir}")
        return template_path.read_text(encoding="utf-8")


def _resolve_plugin_config(context: BootstrapContext) -> HtmlPluginConfig:
    config_dir = (
        context.config.source_path.parent
        if context.config.source_path is not None
        else DEFAULT_CONFIG_DIR
    )

    raw_settings = context.get_settings(PLUGIN_ID, default={})

    site_title_raw = raw_settings.get("site_title", _DEFAULT_SITE_TITLE)
    site_title = str(site_title_raw).strip() or _DEFAULT_SITE_TITLE

    templates_root_raw = raw_settings.get("templates_root")
    if templates_root_raw is None:
        templates_root = config_dir
    else:
        root_path = Path(str(templates_root_raw)).expanduser()
        if not root_path.is_absolute():
            root_path = (config_dir / root_path).resolve()
        templates_root = root_path

    return HtmlPluginConfig(site_title=site_title, templates_root=templates_root)


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


def _current_templates_dir() -> Path:
    return _current_config.templates_root / TEMPLATE_RELATIVE_DIR


def _collect_notes(storage: Storage) -> list[NoteSnapshot]:
    return storage.snapshot_notes()


def _export_html(
    *,
    storage: Storage,
    destination: Path,
    options: Mapping[str, Any] | None = None,
) -> int:
    exporter = HtmlExporter(
        _current_templates_dir(),
        site_title=_current_config.site_title,
    )
    try:
        return exporter.export(_collect_notes(storage), destination)
    except ExportError:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        raise ExportError(f"HTML export failed: {exc}") from exc


@hookimpl
def bootstrap(context: BootstrapContext) -> None:
    """Capture configuration and ensure templates before exporters run."""

    global _current_config
    plugin_config = _resolve_plugin_config(context)
    ensure_templates(plugin_config.templates_root)
    _current_config = plugin_config


@hookimpl
def export_formats() -> tuple[ExportContribution, ...]:
    """Expose the built-in HTML exporter as a plugin contribution."""

    contribution = ExportContribution(
        format_id="html",
        formatter=_export_html,
        description="Static HTML site with search",
    )
    return (contribution,)


__all__ = [
    "HtmlExporter",
    "PLUGIN_ID",
    "bootstrap",
    "ensure_templates",
    "export_formats",
]
