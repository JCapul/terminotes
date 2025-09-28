"""Datetime formatting helpers for consistent, user-friendly display."""

from __future__ import annotations

from datetime import datetime, timezone

# Prior to v0.3.x we rendered timestamps as "YYYY-MM-DD HH:MM UTC".
_LEGACY_UTC_DISPLAY_FORMAT = "%Y-%m-%d %H:%M UTC"


def _format_local(dt: datetime) -> str:
    """Return ``dt`` formatted in the local timezone (minutes precision)."""

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local_dt = dt.astimezone()
    # Use ISO-8601 formatting so the offset survives round trips, but swap "T"
    # for a space to keep the CLI output compact ("YYYY-MM-DD HH:MM±HH:MM").
    return local_dt.isoformat(timespec="minutes").replace("T", " ")


def now_user_friendly_local() -> str:
    """Return current time as a local-time, user-friendly string."""

    return _format_local(datetime.now(tz=timezone.utc))


def to_user_friendly_local(dt: datetime) -> str:
    """Format the provided aware ``datetime`` in the local timezone."""

    return _format_local(dt)


def parse_user_datetime(value: str) -> datetime:
    """Parse a user-provided datetime string into an aware UTC datetime.

    Accepts ISO 8601 strings (with timezone or 'Z'), the current local display
    format (``YYYY-MM-DD HH:MM±HH:MM``), and the legacy UTC format
    (``YYYY-MM-DD HH:MM UTC``).
    """

    if not isinstance(value, str):
        raise ValueError("datetime value must be a string")

    text = value.strip()
    if not text:
        raise ValueError("empty datetime value")

    # Try ISO 8601 first, supporting trailing 'Z'. This also handles strings
    # emitted by ``_format_local``.
    iso_candidate = text.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(iso_candidate)
        if dt.tzinfo is None:
            local_tz = datetime.now(tz=timezone.utc).astimezone().tzinfo or timezone.utc
            dt = dt.replace(tzinfo=local_tz)
        return dt.astimezone(timezone.utc)
    except ValueError:
        pass

    # Fall back to the legacy UTC-only display format used prior to v0.3.x.
    try:
        dt = datetime.strptime(text, _LEGACY_UTC_DISPLAY_FORMAT)
        return dt.replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ValueError(f"unrecognized datetime format: {value}") from exc
