"""Export helpers for Terminotes notes."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Iterable

from .storage import NoteSnapshot


class ExportError(RuntimeError):
    """Raised when exporting notes fails."""


@dataclass(slots=True)
class ExportOptions:
    destination: Path
    site_title: str = "Terminotes"


def _render_body_html(body: str) -> str:
    paragraphs = [segment.strip() for segment in body.split("\n\n") if segment.strip()]
    if not paragraphs:
        return "<p>(No content)</p>"
    html_parts: list[str] = []
    for para in paragraphs:
        escaped = escape(para).replace("\n", "<br />")
        html_parts.append(f"<p>{escaped}</p>")
    return "\n".join(html_parts)


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

    def export(self, notes: Iterable[NoteSnapshot], destination: Path) -> int:
        dest = destination
        dest.mkdir(parents=True, exist_ok=True)

        index_template = self._read_template("index.html")
        note_template = self._read_template("note.html")
        styles_template = self._read_template("styles.css")
        search_js_template = self._read_template("search.js")

        (dest / "styles.css").write_text(styles_template, encoding="utf-8")
        (dest / "search.js").write_text(search_js_template, encoding="utf-8")

        notes_dir = dest / "notes"
        notes_dir.mkdir(exist_ok=True)

        notes_list_markup: list[str] = []
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

            note_markup = (
                note_template.replace("{{title}}", escape(note_title))
                .replace("{{created_at}}", created_pretty)
                .replace("{{created_at_iso}}", note.created_at.isoformat())
                .replace("{{updated_at}}", updated_pretty)
                .replace("{{updated_at_iso}}", note.updated_at.isoformat())
                .replace("{{tags}}", escape(tags_display))
                .replace("{{body_html}}", body_html)
            )
            note_path.write_text(note_markup, encoding="utf-8")

            summary_source = note.description or note.body
            summary = (summary_source or "").strip().splitlines()
            summary_text = summary[0] if summary else ""
            summary_text = summary_text[:200] + ("…" if len(summary_text) > 200 else "")

            note_summary = escape(summary_text) or "(No summary)"
            note_link = escape(note_title)
            notes_list_markup.append(
                """
                <li>
                  <a href="{url}"><h2>{title}</h2></a>
                  <p class="note-meta">Updated {updated}</p>
                  <p>{summary}</p>
                  <p class="note-tags">Tags: {tags}</p>
                </li>
                """.format(
                    url=url,
                    title=note_link,
                    updated=updated_pretty,
                    summary=note_summary,
                    tags=escape(tags_display),
                )
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
                }
            )

        notes_json_path = dest / "notes-data.json"
        notes_json_path.write_text(json.dumps(notes_data, indent=2), encoding="utf-8")

        generated_stamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        notes_markup = "\n".join(notes_list_markup) or "<li>No notes available.</li>"
        rendered_index = (
            index_template.replace("{{site_title}}", escape(self.site_title))
            .replace("{{notes_count}}", str(count))
            .replace("{{generated_at}}", generated_stamp)
            .replace("{{notes_list}}", notes_markup)
        )
        (dest / "index.html").write_text(rendered_index, encoding="utf-8")

        return count

    def _read_template(self, name: str) -> str:
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

            front_matter_lines = ["---"]
            front_matter_lines.append(f"id: {note.id}")
            front_matter_lines.append(f"title: {_yaml_quote(note.title)}")
            front_matter_lines.append(f"description: {_yaml_quote(note.description)}")
            front_matter_lines.append(f"date: {note.created_at.isoformat()}")
            front_matter_lines.append(f"last_edited: {note.updated_at.isoformat()}")
            can_publish_value = "true" if note.can_publish else "false"
            front_matter_lines.append(f"can_publish: {can_publish_value}")
            front_matter_lines.append("tags:")
            for tag in note.tags:
                front_matter_lines.append(f"  - {_yaml_quote(tag)}")
            front_matter_lines.append("---\n")

            body = note.body.rstrip() + "\n"
            file_path.write_text("\n".join(front_matter_lines) + body, encoding="utf-8")

        return count


def _yaml_quote(value: str) -> str:
    if value == "":
        return '""'
    return json.dumps(value)
