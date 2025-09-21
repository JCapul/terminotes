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
        "SELECT note_id, content, tags, created_at, updated_at FROM notes"
    ).fetchone()
    conn.close()

    assert row is not None
    stored_tags = tuple(json.loads(row[2]))
    assert row[0] == note.note_id
    assert row[1] == "Captured message"
    assert stored_tags == note.tags
    assert row[3] == row[4]


def test_create_note_rejects_empty_content(tmp_path) -> None:
    storage = Storage(tmp_path / DB_FILENAME)
    storage.initialize()

    try:
        storage.create_note("   \n", [])
    except StorageError as exc:
        assert "empty" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected StorageError for empty content")


def test_fetch_and_update_note(tmp_path) -> None:
    storage = Storage(tmp_path / DB_FILENAME)
    storage.initialize()

    created = storage.create_note("Title\n\nBody", ["til"])

    fetched = storage.fetch_note(created.note_id)
    assert fetched.note_id == created.note_id
    assert fetched.content == "Title\n\nBody"
    assert fetched.tags == ("til",)

    updated = storage.update_note(created.note_id, "New Title\n\nNew Body", ["python"])
    assert updated.content == "New Title\n\nNew Body"
    assert updated.tags == ("python",)
    assert updated.updated_at >= updated.created_at

    # Ensure persisted update timestamp changed
    assert updated.updated_at > created.updated_at


def test_fetch_last_updated_note(tmp_path) -> None:
    storage = Storage(tmp_path / DB_FILENAME)
    storage.initialize()

    first = storage.create_note("First note", ["til"])
    second = storage.create_note("Second note", ["python"])

    # Update first note to ensure it becomes the most recently edited entry.
    storage.update_note(first.note_id, "First note updated", ["til"])

    latest = storage.fetch_last_updated_note()
    assert latest.note_id == first.note_id
