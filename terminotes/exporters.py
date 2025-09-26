"""Export helpers for Terminotes notes."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Iterable

import yaml
from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape
from markupsafe import Markup

from .storage import NoteSnapshot


class ExportError(RuntimeError):
    """Raised when exporting notes fails."""


@dataclass(slots=True)
class ExportOptions:
    destination: Path
    site_title: str = "Terminotes"


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

    def __init__(self, templates_dir: Path, *, site_title: str = "Terminotes") -> None:
        self.templates_dir = templates_dir
        self.site_title = site_title
        self._env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def export(self, notes: Iterable[NoteSnapshot], destination: Path) -> int:
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


class MarkdownExporter:
    """Render notes into individual Markdown files with YAML front matter."""

    def export(self, notes: Iterable[NoteSnapshot], destination: Path) -> int:
        dest = destination
        dest.mkdir(parents=True, exist_ok=True)

        count = 0
        for note in notes:
            count += 1
            slug = _slugify(note.title or f"note-{note.id}")
            filename = f"{note.id:04d}-{slug}.md"
            file_path = dest / filename

            metadata = {
                "id": note.id,
                "title": note.title or "",
                "description": note.description or "",
                "date": note.created_at.isoformat(),
                "last_edited": note.updated_at.isoformat(),
                "can_publish": bool(note.can_publish),
                "tags": note.tags,
            }

            if note.extra_data is not None:
                metadata["extra_data"] = note.extra_data

            yaml_text = yaml.safe_dump(
                metadata,
                sort_keys=False,
                allow_unicode=True,
                default_flow_style=False,
            ).strip()

            front_matter = f"---\n{yaml_text}\n---\n\n"
            body = (note.body or "").rstrip() + "\n"
            file_path.write_text(front_matter + body, encoding="utf-8")

        return count
