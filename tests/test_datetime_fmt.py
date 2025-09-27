"""Unit tests for datetime formatting helpers."""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone

import pytest
from terminotes.utils.datetime_fmt import (
    parse_user_datetime,
    to_user_friendly_local,
)


@pytest.mark.skipif(
    not hasattr(time, "tzset"),
    reason="time.tzset is required to adjust the local timezone in tests",
)
def test_to_user_friendly_local_reflects_local_offset() -> None:
    original = os.environ.get("TZ")
    os.environ["TZ"] = "America/New_York"
    time.tzset()
    try:
        source = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        formatted = to_user_friendly_local(source)

        # 12:00 UTC -> 07:00 Eastern (UTC-05:00) on 1 Jan 2024.
        assert formatted.startswith("2024-01-01 07:00")
        assert formatted.endswith("-05:00")

        # Ensure the round trip lands back on the original UTC instant.
        parsed = parse_user_datetime(formatted)
        assert parsed == source
    finally:
        if original is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = original
        time.tzset()


def test_parse_user_datetime_accepts_legacy_format() -> None:
    legacy = "2024-01-01 12:34 UTC"
    parsed = parse_user_datetime(legacy)
    expected = datetime(2024, 1, 1, 12, 34, tzinfo=timezone.utc)
    assert parsed == expected
