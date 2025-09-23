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


def parse_user_datetime(value: str) -> datetime:
    """Parse a user-provided datetime string into an aware UTC datetime.

    Accepts ISO 8601 strings (with timezone or 'Z') and the CLI's
    user-friendly format (e.g., '2025-01-31 09:15 UTC').
    """

    if not isinstance(value, str):
        raise ValueError("datetime value must be a string")

    text = value.strip()
    if not text:
        raise ValueError("empty datetime value")

    # Try ISO 8601 first, supporting trailing 'Z'.
    iso_candidate = text.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(iso_candidate)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        pass

    # Try the friendly CLI format.
    try:
        dt = datetime.strptime(text, _DISPLAY_FORMAT)
        return dt.replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ValueError(f"unrecognized datetime format: {value}") from exc
