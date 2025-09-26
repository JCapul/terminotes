"""Helpers for interacting with the Internet Archive Wayback Machine."""

from __future__ import annotations

import httpx

WAYBACK_AVAILABLE_API = "https://archive.org/wayback/available"


def fetch_latest_snapshot(url: str, *, timeout: float = 5.0) -> dict[str, str] | None:
    """Return metadata for the latest archived snapshot of ``url``.

    The result includes at least the snapshot ``url`` and may also contain
    ``timestamp`` and ``status`` fields when provided by the API. ``None`` is
    returned when no snapshot is available or when the request fails.
    """

    target = url.strip()
    if not target:
        return None

    try:
        response = httpx.get(
            WAYBACK_AVAILABLE_API,
            params={"url": target},
            timeout=timeout,
            follow_redirects=True,
        )
        response.raise_for_status()
    except httpx.HTTPError:
        return None

    try:
        payload = response.json()
    except ValueError:
        return None

    archived = payload.get("archived_snapshots")
    if not isinstance(archived, dict):
        return None

    closest = archived.get("closest")
    if not isinstance(closest, dict):
        return None

    snapshot_url = closest.get("url")
    if not isinstance(snapshot_url, str) or not snapshot_url:
        return None

    snapshot: dict[str, str] = {"url": snapshot_url}

    timestamp = closest.get("timestamp")
    if isinstance(timestamp, str) and timestamp:
        snapshot["timestamp"] = timestamp

    status = closest.get("status")
    if isinstance(status, str) and status:
        snapshot["status"] = status

    available = closest.get("available")
    if available is False:
        return None

    return snapshot
