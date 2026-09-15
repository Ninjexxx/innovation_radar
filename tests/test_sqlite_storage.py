import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from innovation_radar.models import RawItem, RunRecord
from innovation_radar.storage.sqlite import SQLiteStorage


def _table_names(database_path: Path) -> set[str]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
        ).fetchall()
    return {row[0] for row in rows}


def test_initializes_sqlite_schema(tmp_path: Path) -> None:
    database_path = tmp_path / "radar.sqlite3"

    SQLiteStorage(database_path).initialize()

    assert database_path.is_file()
    assert _table_names(database_path) == {"raw_items", "run_records", "item_reviews"}


def test_sqlite_initialization_is_idempotent(tmp_path: Path) -> None:
    database_path = tmp_path / "radar.sqlite3"
    storage = SQLiteStorage(database_path)

    storage.initialize()
    with sqlite3.connect(database_path) as connection:
        first_schema_version = connection.execute("PRAGMA schema_version").fetchone()[0]

    storage.initialize()
    with sqlite3.connect(database_path) as connection:
        second_schema_version = connection.execute("PRAGMA schema_version").fetchone()[0]

    assert first_schema_version == second_schema_version
    assert _table_names(database_path) == {"raw_items", "run_records", "item_reviews"}


def test_persists_and_reads_raw_item(tmp_path: Path) -> None:
    storage = SQLiteStorage(tmp_path / "radar.sqlite3")
    storage.initialize()
    timestamp = datetime(2026, 8, 27, 12, 30, tzinfo=timezone.utc)
    item = RawItem(
        id="item-1",
        source="example",
        source_item_id="source-1",
        title="Experimental capability",
        description="A synthetic test item.",
        url="https://example.com/item",
        author="tester",
        published_at=timestamp,
        first_seen_at=timestamp,
        collected_at=timestamp,
        raw_metrics={"votes": 3},
        raw_payload={"source_field": "preserved"},
    )

    storage.save_raw_item(item)

    assert storage.get_raw_item(item.id) == item


def test_reencounter_updates_item_and_preserves_first_seen(tmp_path: Path) -> None:
    storage = SQLiteStorage(tmp_path / "radar.sqlite3")
    storage.initialize()
    first_seen = datetime(2026, 8, 27, 12, 30, tzinfo=timezone.utc)
    collected_again = datetime(2026, 8, 27, 13, 30, tzinfo=timezone.utc)
    original = RawItem(
        id="original-id",
        source="hacker_news",
        source_item_id="123",
        title="Original title",
        url="https://example.com/original",
        first_seen_at=first_seen,
        collected_at=first_seen,
        raw_metrics={"score": 1},
        raw_payload={"version": 1},
    )
    rediscovered = RawItem(
        id="different-internal-id",
        source="hacker_news",
        source_item_id="123",
        title="Updated title",
        url="https://example.com/updated",
        first_seen_at=collected_again,
        collected_at=collected_again,
        raw_metrics={"score": 8},
        raw_payload={"version": 2},
    )

    assert storage.save_raw_item(original) is True
    assert storage.save_raw_item(rediscovered) is False

    stored = storage.get_raw_item_by_source("hacker_news", "123")
    assert stored is not None
    assert storage.count_raw_items() == 1
    assert stored.id == original.id
    assert stored.first_seen_at == first_seen
    assert stored.collected_at == collected_again
    assert stored.title == "Updated title"
    assert stored.raw_metrics == {"score": 8}
    assert stored.raw_payload == {"version": 2}


def test_persists_and_reads_run_record(tmp_path: Path) -> None:
    storage = SQLiteStorage(tmp_path / "radar.sqlite3")
    storage.initialize()
    started_at = datetime(2026, 8, 27, 12, 30, tzinfo=timezone.utc)
    finished_at = datetime(2026, 8, 27, 12, 31, tzinfo=timezone.utc)
    run = RunRecord(
        id="run-1",
        started_at=started_at,
        finished_at=finished_at,
        status="completed",
    )

    storage.save_run_record(run)

    assert storage.get_run_record(run.id) == run


def test_counts_known_items_refreshed_during_run(tmp_path: Path) -> None:
    storage = SQLiteStorage(tmp_path / "radar.sqlite3")
    storage.initialize()
    first_seen = datetime(2026, 8, 27, 12, 0, tzinfo=timezone.utc)
    refreshed_at = datetime(2026, 8, 27, 13, 1, tzinfo=timezone.utc)
    run = RunRecord(
        id="run-refresh",
        started_at=datetime(2026, 8, 27, 13, 0, tzinfo=timezone.utc),
        finished_at=datetime(2026, 8, 27, 13, 2, tzinfo=timezone.utc),
        status="completed",
    )
    original = RawItem(
        id="item-known",
        source="example",
        source_item_id="known",
        title="Known item",
        url="https://example.com/known",
        first_seen_at=first_seen,
        collected_at=first_seen,
    )
    refreshed = RawItem(
        id="item-known",
        source="example",
        source_item_id="known",
        title="Known item",
        url="https://example.com/known",
        first_seen_at=refreshed_at,
        collected_at=refreshed_at,
    )

    storage.save_raw_item(original)
    storage.save_raw_item(refreshed)

    assert storage.count_reencountered_items(run) == 1
