"""Utility script to strip trailing markdown links from link-tagged notes."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from terminotes.storage import DB_FILENAME, Note, Storage, StorageError, Tag

_MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)\s*$")
_BULLET_PREFIXES: tuple[str, ...] = ("- ", "* ", "+ ")


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=("Remove trailing markdown link lines from notes tagged 'link'.")
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=Path.cwd() / DB_FILENAME,
        help=("Path to the terminotes SQLite database. Defaults to ./" + DB_FILENAME),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the cleanup without persisting any changes.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print updated bodies for each modified note.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    db_path = args.db_path.expanduser()
    if not db_path.exists():
        print(f"Database not found at {db_path}", file=sys.stderr)
        return 1
    storage = Storage(db_path)

    try:
        notes = _fetch_link_tagged_notes(storage)
    except StorageError as exc:
        print(f"Failed to load notes: {exc}", file=sys.stderr)
        return 1

    if not notes:
        print("No notes tagged 'link' found.")
        return 0

    total_changes = 0
    total_removed = 0

    for note in notes:
        expected_urls = _link_urls_from_extra(note.extra_data)
        result = _cleanup_body(note.body, expected_urls)
        if result is None:
            continue

        total_changes += 1
        total_removed += len(result.removed_urls)
        _print_preview(note.id, result.removed_urls, args.verbose, result.updated_body)

        if not args.dry_run:
            storage.update_note(
                note_id=note.id,
                title=note.title,
                body=result.updated_body,
                description=note.description,
                created_at=note.created_at,
                updated_at=note.updated_at,
            )

    if total_changes == 0:
        print("No trailing markdown links detected; nothing to do.")
        return 0

    if args.dry_run:
        print(
            f"Dry run complete. Would update {total_changes} notes "
            f"and remove {total_removed} link lines."
        )
    else:
        print(f"Updated {total_changes} notes and removed {total_removed} link lines.")

    return 0


def _fetch_link_tagged_notes(storage: Storage) -> list[Note]:
    through_model = storage._through_model
    with storage._connection():
        query = (
            Note.select()
            .join(through_model, on=(through_model.note == Note.id))
            .join(Tag)
            .where(Tag.name == "link")
            .distinct()
            .order_by(Note.id)
        )
        return list(query)


def _link_urls_from_extra(raw_extra: str | None) -> set[str]:
    if not raw_extra:
        return set()
    try:
        parsed = json.loads(raw_extra)
    except json.JSONDecodeError:
        return set()
    if not isinstance(parsed, dict):
        return set()
    link_data = parsed.get("link")
    if not isinstance(link_data, dict):
        return set()
    urls: set[str] = set()
    source = link_data.get("source_url")
    if isinstance(source, str) and source.strip():
        urls.add(source.strip())
    wayback = link_data.get("wayback")
    if isinstance(wayback, str) and wayback.strip():
        urls.add(wayback.strip())
    return urls


@dataclass(slots=True)
class _BodyCleanup:
    removed_urls: tuple[str, ...]
    updated_body: str


def _cleanup_body(body: str, expected_urls: set[str]) -> _BodyCleanup | None:
    if not body:
        return None

    lines = body.rstrip().split("\n")
    if not lines:
        return None

    removed_urls: list[str] = []

    while lines:
        candidate = lines[-1]
        stripped = candidate.strip()

        if not stripped:
            lines.pop()
            continue

        link = _extract_markdown_link(stripped)
        if link is None:
            break

        label, url = link
        if expected_urls and url not in expected_urls:
            break

        if not expected_urls and label.lower() not in {
            "link",
            "source",
            "wayback",
            "archive",
        }:
            break

        removed_urls.append(url)
        lines.pop()

    if not removed_urls:
        return None

    while lines and not lines[-1].strip():
        lines.pop()

    updated_body = "\n".join(lines).rstrip()
    return _BodyCleanup(
        removed_urls=tuple(reversed(removed_urls)), updated_body=updated_body
    )


def _extract_markdown_link(line: str) -> tuple[str, str] | None:
    stripped = line
    for prefix in _BULLET_PREFIXES:
        if stripped.startswith(prefix):
            stripped = stripped[len(prefix) :].strip()
            break
    if stripped and stripped[0].isdigit():
        prefix = stripped.split(" ", 1)[0]
        if prefix.endswith(".") or prefix.endswith(")"):
            parts = stripped.split(" ", 1)
            if len(parts) == 2:
                stripped = parts[1].strip()
    match = _MARKDOWN_LINK_RE.search(stripped)
    if not match:
        return None
    label = match.group(1).strip()
    url = match.group(2).strip()
    if not url.lower().startswith(("http://", "https://")):
        return None
    return label, url


def _print_preview(
    note_id: int,
    removed_urls: Iterable[str],
    verbose: bool,
    updated_body: str,
) -> None:
    removed_list = ", ".join(removed_urls)
    print(f"Note {note_id}: removed {removed_list or 'no URLs'}")
    if verbose:
        print("New body:\n---")
        print(updated_body)
        print("---")


if __name__ == "__main__":
    sys.exit(main())
