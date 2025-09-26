"""Tests for the Peewee-backed storage layer."""

from __future__ import annotations

from terminotes.storage import DB_FILENAME, Storage, StorageError


def test_create_note_persists_content(tmp_path) -> None:
    db_path = tmp_path / DB_FILENAME
    storage = Storage(db_path)
    storage.initialize()

    note = storage.create_note("Captured message", "")

    assert isinstance(note.id, int) and note.id >= 1

    stored = storage.fetch_note(note.id)
    assert stored.id == note.id
    assert stored.title == "Captured message"
    assert stored.body == ""
    assert stored.description == ""
    assert stored.created_at == stored.updated_at


def test_create_note_rejects_empty_content(tmp_path) -> None:
    storage = Storage(tmp_path / DB_FILENAME)
    storage.initialize()

    try:
        storage.create_note("   \n", "   \n", [])
    except StorageError as exc:
        assert "empty" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected StorageError for empty content")


def test_fetch_and_update_note(tmp_path) -> None:
    storage = Storage(tmp_path / DB_FILENAME)
    storage.initialize()

    created = storage.create_note("Title", "Body")

    fetched = storage.fetch_note(created.id)
    assert fetched.id == created.id
    assert fetched.title == "Title"
    assert fetched.body == "Body"

    updated = storage.update_note(created.id, "New Title", "New Body")
    assert updated.title == "New Title"
    assert updated.body == "New Body"
    assert updated.updated_at >= updated.created_at

    # Ensure persisted update timestamp changed
    assert updated.updated_at > created.updated_at


def test_fetch_last_updated_note(tmp_path) -> None:
    storage = Storage(tmp_path / DB_FILENAME)
    storage.initialize()

    first = storage.create_note("First note", "")
    storage.create_note("Second note", "")

    # Update first note to ensure it becomes the most recently edited entry.
    storage.update_note(first.id, "First note updated", "")

    latest = storage.fetch_last_updated_note()
    assert latest.id == first.id
