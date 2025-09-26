from __future__ import annotations

import json
from datetime import datetime, timezone

import yaml
from terminotes.config import ensure_export_templates
from terminotes.exporters import HtmlExporter, MarkdownExporter
from terminotes.storage import NoteSnapshot


def _sample_note(
    note_id: int,
    title: str,
    *,
    tags: list[str] | None = None,
    extra_data: dict[str, object] | None = None,
) -> NoteSnapshot:
    now = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    return NoteSnapshot(
        id=note_id,
        title=title,
        body="Line 1\n\nLine 2",
        description="Sample description",
        created_at=now,
        updated_at=now,
        can_publish=False,
        tags=tags or [],
        extra_data=extra_data,
    )


def test_html_exporter_writes_site(tmp_path) -> None:
    ensure_export_templates(tmp_path)
    templates_dir = tmp_path / "templates" / "export" / "html"

    exporter = HtmlExporter(templates_dir, site_title="My Notes")
    notes = [
        _sample_note(
            1,
            "Note One",
            tags=["work"],
            extra_data={"link": {"source_url": "https://example.com"}},
        )
    ]

    destination = tmp_path / "site"
    count = exporter.export(notes, destination)

    assert count == 1
    index_html = (destination / "index.html").read_text(encoding="utf-8")
    assert "My Notes" in index_html
    assert "Note One" in index_html

    note_file = next((destination / "notes").glob("*.html"))
    assert "Line 1" in note_file.read_text(encoding="utf-8")

    data = json.loads((destination / "notes-data.json").read_text(encoding="utf-8"))
    assert data[0]["title"] == "Note One"
    assert data[0]["extra_data"] == {"link": {"source_url": "https://example.com"}}


def test_markdown_exporter_writes_front_matter(tmp_path) -> None:
    exporter = MarkdownExporter()
    notes = [_sample_note(2, "Markdown Note", tags=["personal", "ideas"])]

    destination = tmp_path / "markdown"
    count = exporter.export(notes, destination)

    assert count == 1
    file_path = next(destination.glob("*.md"))
    content = file_path.read_text(encoding="utf-8")
    assert content.startswith("---\nid: 2")
    assert "title: Markdown Note" in content
    assert "tags:\n- personal\n- ideas" in content
    assert content.strip().endswith("Line 2")


def test_markdown_exporter_includes_extra_data(tmp_path) -> None:
    exporter = MarkdownExporter()
    snapshot = _sample_note(
        3,
        "Link Note",
        extra_data={"link": {"source_url": "https://example.com"}},
    )

    destination = tmp_path / "md"
    exporter.export([snapshot], destination)

    file_path = next(destination.glob("*.md"))
    content = file_path.read_text(encoding="utf-8")
    metadata = yaml.safe_load(content.split("---\n", 2)[1])
    assert metadata["extra_data"] == {"link": {"source_url": "https://example.com"}}
