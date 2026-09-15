from datetime import datetime, timedelta, timezone

import pytest

from innovation_radar.models import RawItem, RunRecord


def test_raw_item_normalizes_aware_datetimes_to_utc() -> None:
    local_timezone = timezone(timedelta(hours=-3))
    timestamp = datetime(2026, 8, 27, 9, 30, tzinfo=local_timezone)

    item = RawItem(
        id="item-1",
        source="example",
        source_item_id="source-1",
        title="Example item",
        url="https://example.com/item",
        published_at=timestamp,
        first_seen_at=timestamp,
        collected_at=timestamp,
    )

    expected = datetime(2026, 8, 27, 12, 30, tzinfo=timezone.utc)
    assert item.published_at == expected
    assert item.first_seen_at == expected
    assert item.collected_at == expected


def test_models_reject_naive_datetimes() -> None:
    naive_timestamp = datetime(2026, 8, 27, 12, 30)

    with pytest.raises(ValueError, match="timezone-aware"):
        RunRecord(
            id="run-1",
            started_at=naive_timestamp,
            status="started",
        )
