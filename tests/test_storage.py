"""Tests for the Peewee-backed storage layer."""

from __future__ import annotations

import json
import sqlite3

import pytest
from terminotes.storage import DB_FILENAME, TABLE_TAGS, Storage, StorageError


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
    assert list(stored.tags) == []


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


def test_tags_created_and_updated(tmp_path) -> None:
    storage = Storage(tmp_path / DB_FILENAME)
    storage.initialize()

    created = storage.create_note("Tagged", "Body", tags=["Work", "personal", "Work"])
    assert sorted(tag.name for tag in created.tags) == ["personal", "work"]

    updated = storage.update_note(created.id, "Tagged", "Body", tags=["focus"])
    assert [tag.name for tag in updated.tags] == ["focus"]

    cleared = storage.update_note(created.id, "Tagged", "Body", tags=[])
    assert list(cleared.tags) == []

    fetched = storage.fetch_note(created.id)
    assert list(fetched.tags) == []


def test_create_note_rolls_back_on_tag_failure(tmp_path, monkeypatch) -> None:
    storage = Storage(tmp_path / DB_FILENAME)
    storage.initialize()

    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("terminotes.storage.Tag.get_or_create", boom)

    with pytest.raises(StorageError):
        storage.create_note("Title", "Body", tags=["fail"])

    assert storage.count_notes() == 0


def test_list_notes_requires_all_tags(tmp_path) -> None:
    storage = Storage(tmp_path / DB_FILENAME)
    storage.initialize()

    alpha = storage.create_note("Alpha", "Body", tags=["work", "focus"])
    storage.create_note("Beta", "Body", tags=["work"])
    storage.create_note("Gamma", "Body", tags=["focus"])

    filtered = storage.list_notes(tags=["work", "focus"])

    assert [note.id for note in filtered] == [alpha.id]


def test_extra_data_round_trip(tmp_path) -> None:
    storage = Storage(tmp_path / DB_FILENAME)
    storage.initialize()

    payload = {
        "link": {"source_url": "https://example.com", "wayback": "https://archive"}
    }
    created = storage.create_note("Link note", "Body", extra_data=payload)

    fetched = storage.fetch_note(created.id)
    assert fetched.extra_data is not None
    assert json.loads(fetched.extra_data) == payload

    snapshot = storage.snapshot_notes()[0]
    assert snapshot.extra_data == payload

    storage.update_note(created.id, "Link note", "Body", extra_data=None)
    refetched = storage.fetch_note(created.id)
    assert refetched.extra_data is None


def test_delete_note_removes_associations(tmp_path) -> None:
    storage = Storage(tmp_path / DB_FILENAME)
    storage.initialize()

    created = storage.create_note("Tagged", "Body", tags=["work", "focus"])
    assert sorted(tag.name for tag in created.tags) == ["focus", "work"]

    storage.delete_note(created.id)

    assert storage.count_notes() == 0
    with pytest.raises(StorageError):
        storage.fetch_note(created.id)

    # New note with same tags succeeds once associations are cleared.
    replacement = storage.create_note("Fresh", "Body", tags=["work"])
    assert storage.count_notes() == 1
    assert replacement.title == "Fresh"


def test_prune_unused_tags_removes_orphans(tmp_path) -> None:
    storage = Storage(tmp_path / DB_FILENAME)
    storage.initialize()

    note = storage.create_note("Tagged", "Body", tags=["focus"])
    # Clearing tags leaves a dangling 'focus' entry in the tags table.
    storage.update_note(note.id, "Tagged", "Body", tags=[])

    result = storage.prune_unused_tags()

    assert result.removed_links == 0
    assert result.removed_tags == 1

    conn = sqlite3.connect(storage.path)
    try:
        remaining = conn.execute(f"SELECT COUNT(*) FROM {TABLE_TAGS}").fetchone()
    finally:
        conn.close()

    assert remaining is not None and int(remaining[0]) == 0
