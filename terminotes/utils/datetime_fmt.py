"""Datetime formatting utilities for consistent, user-friendly display."""

from __future__ import annotations

from datetime import datetime, timezone

# Fixed, universal, user-friendly format: "YYYY-MM-DD HH:MM UTC"
# We always render timestamps in UTC to avoid locale/timezone ambiguity.
_DISPLAY_FORMAT = "%Y-%m-%d %H:%M UTC"


def now_user_friendly_utc() -> str:
    """Return current time as a user-friendly UTC string.

    Example: "2025-01-31 09:15 UTC"
    """

    return datetime.now(tz=timezone.utc).strftime(_DISPLAY_FORMAT)


def to_user_friendly_utc(dt: datetime) -> str:
    """Format the provided aware ``datetime`` in UTC using a friendly format."""

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime(_DISPLAY_FORMAT)
