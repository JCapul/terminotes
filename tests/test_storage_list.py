from __future__ import annotations

from datetime import datetime, timedelta, timezone

from terminotes.storage import DB_FILENAME, Storage


def test_list_notes_orders_by_updated_desc_and_limits(tmp_path) -> None:
    db_path = tmp_path / DB_FILENAME
    storage = Storage(db_path)
    storage.initialize()

    base = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)

    a = storage.create_note("A", "", created_at=base, updated_at=base)
    b = storage.create_note(
        "B",
        "",
        created_at=base + timedelta(minutes=1),
        updated_at=base + timedelta(minutes=1),
    )
    c = storage.create_note(
        "C",
        "",
        created_at=base + timedelta(minutes=2),
        updated_at=base + timedelta(minutes=2),
    )

    # Ensure update order can change; bump A to be most recent
    storage.update_note(a.id, "A*", "", updated_at=base + timedelta(minutes=3))

    result = list(storage.list_notes(limit=10))
    ids = [n.id for n in result]
    # Expect A (updated last), then C, then B
    assert ids == [a.id, c.id, b.id]

    limited = list(storage.list_notes(limit=2))
    assert [n.id for n in limited] == [a.id, c.id]


def test_list_notes_filters_by_tags(tmp_path) -> None:
    db_path = tmp_path / DB_FILENAME
    storage = Storage(db_path)
    storage.initialize()

    base = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)

    a = storage.create_note("A", "", created_at=base, updated_at=base, tags=["work"])
    b = storage.create_note(
        "B",
        "",
        created_at=base,
        updated_at=base,
        tags=["personal"],
    )
    c = storage.create_note(
        "C",
        "",
        created_at=base,
        updated_at=base,
        tags=["work", "personal"],
    )

    filtered = list(storage.list_notes(limit=10, tags=["work"]))
    assert {n.id for n in filtered} == {a.id, c.id}

    filtered_personal = list(storage.list_notes(limit=10, tags=["personal"]))
    assert {n.id for n in filtered_personal} == {b.id, c.id}
