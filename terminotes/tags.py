"""Tag utilities for validation and normalization."""

from __future__ import annotations

from typing import Iterable, Tuple


def normalize_against_allowed(
    allowed_tags: Iterable[str], incoming: Iterable[str]
) -> Tuple[tuple[str, ...], tuple[str, ...]]:
    """Return (valid_tags, unknown_tags) preserving order and removing duplicates.

    - Only tags present in ``allowed_tags`` are kept.
    - Tags are de-duplicated while preserving the first occurrence order.
    - Unknown tags are returned in the order they appeared.
    """

    allowed = set(allowed_tags)
    original = list(incoming)

    valid_ordered: list[str] = []
    seen: set[str] = set()
    unknown: list[str] = []

    for tag in original:
        if tag in allowed:
            if tag not in seen:
                valid_ordered.append(tag)
                seen.add(tag)
        else:
            unknown.append(tag)

    return tuple(valid_ordered), tuple(unknown)
