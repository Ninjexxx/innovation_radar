"""SQLite persistence for collected items and execution records."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator

from innovation_radar.models import ItemReview, RawItem, RunRecord


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS raw_items (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    source_item_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    url TEXT NOT NULL,
    author TEXT,
    published_at TEXT,
    first_seen_at TEXT NOT NULL,
    collected_at TEXT NOT NULL,
    raw_metrics TEXT NOT NULL DEFAULT '{}',
    raw_payload TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_raw_items_source_item
    ON raw_items (source, source_item_id);

CREATE TABLE IF NOT EXISTS run_records (
    id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS item_reviews (
    item_id TEXT PRIMARY KEY,
    human_label TEXT NOT NULL,
    human_reason TEXT,
    reviewed_at TEXT NOT NULL
);
"""


def _datetime_to_text(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat(timespec="microseconds").replace("+00:00", "Z")


def _datetime_from_text(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _json_to_text(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


class SQLiteStorage:
    """Persist raw items and run records in one local SQLite database."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    def initialize(self) -> None:
        """Create the database and schema, safely repeatable."""

        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            connection.executescript(SCHEMA_SQL)

    def save_raw_item(self, item: RawItem) -> bool:
        """Insert or update an item, returning True only for a new identity."""

        return self.upsert_raw_items((item,))[0]

    def upsert_raw_items(self, items: Iterable[RawItem]) -> list[bool]:
        """Persist one source batch atomically and report new/known identities."""

        results: list[bool] = []
        with self._connection() as connection:
            for item in items:
                results.append(self._upsert_raw_item(connection, item))
        return results

    def get_raw_item(self, item_id: str) -> RawItem | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM raw_items WHERE id = ?", (item_id,)
            ).fetchone()

        return _raw_item_from_row(row) if row is not None else None

    def get_raw_item_by_source(
        self, source: str, source_item_id: str
    ) -> RawItem | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM raw_items WHERE source = ? AND source_item_id = ?",
                (source, source_item_id),
            ).fetchone()
        return _raw_item_from_row(row) if row is not None else None

    def count_raw_items(self) -> int:
        with self._connection() as connection:
            row = connection.execute("SELECT COUNT(*) FROM raw_items").fetchone()
        return int(row[0])

    def list_raw_items(self) -> tuple[RawItem, ...]:
        """Return persisted items in stable insertion order."""

        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM raw_items ORDER BY rowid"
            ).fetchall()
        return tuple(_raw_item_from_row(row) for row in rows)

    def save_reviews(self, reviews: Iterable[ItemReview]) -> int:
        """Persist human review decisions; re-marking an item updates it in place."""

        count = 0
        with self._connection() as connection:
            for review in reviews:
                connection.execute(
                    """
                    INSERT INTO item_reviews (
                        item_id, human_label, human_reason, reviewed_at
                    ) VALUES (?, ?, ?, ?)
                    ON CONFLICT(item_id) DO UPDATE SET
                        human_label = excluded.human_label,
                        human_reason = excluded.human_reason,
                        reviewed_at = excluded.reviewed_at
                    """,
                    (
                        review.item_id,
                        review.human_label,
                        review.human_reason,
                        _datetime_to_text(review.reviewed_at),
                    ),
                )
                count += 1
        return count

    def reviewed_item_ids(self) -> set[str]:
        """Return the ids of all items that already received a human review."""

        with self._connection() as connection:
            rows = connection.execute("SELECT item_id FROM item_reviews").fetchall()
        return {row["item_id"] for row in rows}

    def count_reviews(self) -> int:
        with self._connection() as connection:
            row = connection.execute("SELECT COUNT(*) FROM item_reviews").fetchone()
        return int(row[0])

    def save_run_record(self, run: RunRecord) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO run_records (
                    id, started_at, finished_at, status, error_message
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    finished_at = excluded.finished_at,
                    status = excluded.status,
                    error_message = excluded.error_message
                """,
                (
                    run.id,
                    _datetime_to_text(run.started_at),
                    _datetime_to_text(run.finished_at),
                    run.status,
                    run.error_message,
                ),
            )

    def get_run_record(self, run_id: str) -> RunRecord | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM run_records WHERE id = ?", (run_id,)
            ).fetchone()

        if row is None:
            return None

        return RunRecord(
            id=row["id"],
            started_at=_required_datetime(row["started_at"]),
            finished_at=_datetime_from_text(row["finished_at"]),
            status=row["status"],
            error_message=row["error_message"],
        )

    def get_latest_run_record(self) -> RunRecord | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM run_records ORDER BY started_at DESC, id DESC LIMIT 1"
            ).fetchone()

        if row is None:
            return None
        return RunRecord(
            id=row["id"],
            started_at=_required_datetime(row["started_at"]),
            finished_at=_datetime_from_text(row["finished_at"]),
            status=row["status"],
            error_message=row["error_message"],
        )

    def count_reencountered_items(self, run: RunRecord) -> int:
        """Count known identities refreshed during one completed run window."""

        if run.finished_at is None:
            return 0
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*)
                FROM raw_items
                WHERE collected_at >= ?
                  AND collected_at <= ?
                  AND first_seen_at < collected_at
                """,
                (
                    _datetime_to_text(run.started_at),
                    _datetime_to_text(run.finished_at),
                ),
            ).fetchone()
        return int(row[0])

    def _upsert_raw_item(
        self, connection: sqlite3.Connection, item: RawItem
    ) -> bool:
        existing = connection.execute(
            "SELECT id FROM raw_items WHERE source = ? AND source_item_id = ?",
            (item.source, item.source_item_id),
        ).fetchone()

        values = (
            item.id,
            item.source,
            item.source_item_id,
            item.title,
            item.description,
            item.url,
            item.author,
            _datetime_to_text(item.published_at),
            _datetime_to_text(item.first_seen_at),
            _datetime_to_text(item.collected_at),
            _json_to_text(item.raw_metrics),
            _json_to_text(item.raw_payload) if item.raw_payload is not None else None,
        )
        if existing is None:
            connection.execute(
                """
                INSERT INTO raw_items (
                    id, source, source_item_id, title, description, url, author,
                    published_at, first_seen_at, collected_at, raw_metrics,
                    raw_payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )
            return True

        connection.execute(
            """
            UPDATE raw_items SET
                title = ?,
                description = COALESCE(?, description),
                url = ?,
                author = COALESCE(?, author),
                published_at = COALESCE(?, published_at),
                collected_at = ?,
                raw_metrics = ?,
                raw_payload = COALESCE(?, raw_payload)
            WHERE source = ? AND source_item_id = ?
            """,
            (
                item.title,
                item.description,
                item.url,
                item.author,
                _datetime_to_text(item.published_at),
                _datetime_to_text(item.collected_at),
                _json_to_text(item.raw_metrics),
                (
                    _json_to_text(item.raw_payload)
                    if item.raw_payload is not None
                    else None
                ),
                item.source,
                item.source_item_id,
            ),
        )
        return False

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()


def _required_datetime(value: str) -> datetime:
    parsed = _datetime_from_text(value)
    if parsed is None:  # Defensive guard for rows outside the managed schema.
        raise ValueError("required datetime is missing")
    return parsed


def _raw_item_from_row(row: sqlite3.Row) -> RawItem:
    return RawItem(
        id=row["id"],
        source=row["source"],
        source_item_id=row["source_item_id"],
        title=row["title"],
        description=row["description"],
        url=row["url"],
        author=row["author"],
        published_at=_datetime_from_text(row["published_at"]),
        first_seen_at=_required_datetime(row["first_seen_at"]),
        collected_at=_required_datetime(row["collected_at"]),
        raw_metrics=json.loads(row["raw_metrics"]),
        raw_payload=(
            json.loads(row["raw_payload"])
            if row["raw_payload"] is not None
            else None
        ),
    )
