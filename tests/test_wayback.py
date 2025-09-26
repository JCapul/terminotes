"""Tests for the Wayback integration helpers."""

from __future__ import annotations

import httpx
import pytest
from terminotes.utils.wayback import fetch_latest_snapshot


class DummyResponse:
    def __init__(self, json_data: dict[str, object], status_code: int = 200) -> None:
        self._json_data = json_data
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPError("error")

    def json(self) -> dict[str, object]:
        return self._json_data


@pytest.fixture
def patch_httpx_get(monkeypatch):
    calls: list[dict[str, object]] = []

    def _fake_get(*args, **kwargs):
        params = kwargs.get("params", {})
        calls.append({"args": args, "params": params})
        payload = kwargs.pop("_payload")
        status = kwargs.pop("_status", 200)
        return DummyResponse(payload, status_code=status)

    def _set(payload: dict[str, object], status: int = 200):
        monkeypatch.setattr(
            httpx,
            "get",
            lambda *a, **k: _fake_get(*a, _payload=payload, _status=status, **k),
        )
        return calls

    return _set


def test_fetch_latest_snapshot_returns_data(patch_httpx_get) -> None:
    payload = {
        "archived_snapshots": {
            "closest": {
                "available": True,
                "url": "https://web.archive.org/example",
                "timestamp": "20240101000000",
                "status": "200",
            }
        }
    }
    patch_httpx_get(payload)

    snapshot = fetch_latest_snapshot("https://example.com")
    assert snapshot == {
        "url": "https://web.archive.org/example",
        "timestamp": "20240101000000",
        "status": "200",
    }


def test_fetch_latest_snapshot_handles_missing(patch_httpx_get) -> None:
    payload = {"archived_snapshots": {}}
    patch_httpx_get(payload)

    snapshot = fetch_latest_snapshot("https://example.com")
    assert snapshot is None


def test_fetch_latest_snapshot_handles_http_error(monkeypatch) -> None:
    def _raise(*_args, **_kwargs):
        raise httpx.HTTPError("boom")

    monkeypatch.setattr(httpx, "get", _raise)

    snapshot = fetch_latest_snapshot("https://example.com")
    assert snapshot is None
