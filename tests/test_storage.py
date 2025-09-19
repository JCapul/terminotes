"""Tests for the SQLite storage layer."""

from __future__ import annotations

import json
import sqlite3

from terminotes.storage import DB_FILENAME, Storage, StorageError


def test_create_note_persists_content_and_tags(tmp_path) -> None:
    db_path = tmp_path / DB_FILENAME
    storage = Storage(db_path)
    storage.initialize()

    note = storage.create_note("Captured message", ["til", "python"])

    assert note.note_id
    assert note.tags == ("til", "python")

    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT note_id, content, tags, created_at FROM notes"
    ).fetchone()
    conn.close()

    assert row is not None
    stored_tags = tuple(json.loads(row[2]))
    assert row[0] == note.note_id
    assert row[1] == "Captured message"
    assert stored_tags == note.tags


def test_create_note_rejects_empty_content(tmp_path) -> None:
    storage = Storage(tmp_path / DB_FILENAME)
    storage.initialize()

    try:
        storage.create_note("   \n", [])
    except StorageError as exc:
        assert "empty" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected StorageError for empty content")
