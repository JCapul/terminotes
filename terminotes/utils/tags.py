"""Hashtag extraction utilities."""

from __future__ import annotations

import re

_HASHTAG_RE = re.compile(r"(?<!\w)#([A-Za-z0-9_][A-Za-z0-9_-]*)")


def extract_hashtags(text: str) -> tuple[str, ...]:
    """Extract unique, lowercase hashtags from ``text`` in first-seen order.

    Rules:
    - Matches ``#tag`` where ``#`` is not preceded by a word character.
    - Captures alphanumerics and underscores after ``#``.
    - Ignores Markdown headings like ``# Title`` (space after ``#``).
    - Deduplicates while preserving first occurrence order.
    """

    seen: set[str] = set()
    ordered: list[str] = []
    for match in _HASHTAG_RE.finditer(text or ""):
        tag = match.group(1).lower()
        if tag and tag not in seen:
            seen.add(tag)
            ordered.append(tag)
    return tuple(ordered)
