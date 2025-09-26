"""Tests for naive LIKE-based search in storage."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from terminotes.storage import DB_FILENAME, Storage


def test_search_matches_title_body_description_and_orders(tmp_path) -> None:
    db_path = tmp_path / DB_FILENAME
    storage = Storage(db_path)
    storage.initialize()

    base = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)

    storage.create_note(
        "Alpha note",
        "foo body",
        "desc one",
        created_at=base,
        updated_at=base,
    )
    b = storage.create_note(
        "Title",
        "contains NeedLe here",
        "desc two",
        created_at=base,
        updated_at=base + timedelta(minutes=1),
    )
    c = storage.create_note(
        "Needle in title",
        "bar",
        "desc three",
        created_at=base,
        updated_at=base + timedelta(minutes=2),
    )
    d = storage.create_note(
        "Delta",
        "baz",
        "description has needle",
        created_at=base,
        updated_at=base + timedelta(minutes=3),
    )

    res = list(storage.search_notes("needle"))
    ids = [n.id for n in res]
    # Expect order by updated_at DESC among matching b, c, d
    assert ids == [d.id, c.id, b.id]

    # No matches
    assert list(storage.search_notes("nomatch")) == []


def test_search_filters_by_tags(tmp_path) -> None:
    db_path = tmp_path / DB_FILENAME
    storage = Storage(db_path)
    storage.initialize()

    base = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)

    a = storage.create_note(
        "Alpha",
        "needle here",
        created_at=base,
        updated_at=base,
        tags=["work"],
    )
    b = storage.create_note(
        "Beta",
        "needle again",
        created_at=base,
        updated_at=base + timedelta(minutes=1),
        tags=["personal"],
    )
    c = storage.create_note(
        "Gamma",
        "another needle",
        created_at=base,
        updated_at=base + timedelta(minutes=2),
        tags=["work", "personal"],
    )

    work_matches = list(storage.search_notes("needle", tags=["work"]))
    assert {n.id for n in work_matches} == {a.id, c.id}

    personal_matches = list(storage.search_notes("needle", tags=["personal"]))
    assert {n.id for n in personal_matches} == {b.id, c.id}
