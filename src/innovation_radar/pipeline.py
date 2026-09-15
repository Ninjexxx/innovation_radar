"""Sequential discovery pipeline for independent collectors."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from innovation_radar.collectors.base import CollectionFailure, Collector
from innovation_radar.filtering.deterministic import (
    ShadowFilterReport,
    evaluate_in_shadow,
)
from innovation_radar.models import RawItem, RunRecord
from innovation_radar.storage.sqlite import SQLiteStorage


Clock = Callable[[], datetime]


@dataclass(frozen=True, slots=True)
class SourceStats:
    source: str
    total: int
    new: int
    updated: int


@dataclass(frozen=True, slots=True)
class DiscoveryResult:
    run_record: RunRecord
    items: tuple[RawItem, ...]
    source_stats: tuple[SourceStats, ...]
    failures: tuple[CollectionFailure, ...]
    filter_report: ShadowFilterReport

    @property
    def total(self) -> int:
        return len(self.items)

    @property
    def new_count(self) -> int:
        return sum(stats.new for stats in self.source_stats)

    @property
    def updated_count(self) -> int:
        return sum(stats.updated for stats in self.source_stats)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def run_discovery(
    storage: SQLiteStorage,
    collectors: Iterable[Collector],
    clock: Clock = utc_now,
    run_id: str | None = None,
) -> DiscoveryResult:
    """Run collectors sequentially while isolating source-level failures."""

    storage.initialize()
    started_at = clock()
    record_id = run_id or str(uuid4())
    storage.save_run_record(
        RunRecord(id=record_id, started_at=started_at, status="running")
    )

    collected_items: list[RawItem] = []
    failures: list[CollectionFailure] = []
    stats: dict[str, list[int]] = {}

    for collector in collectors:
        try:
            batch = collector.collect(clock())
        except Exception as error:
            failures.append(
                CollectionFailure(collector.name, "collector", str(error))
            )
            continue

        failures.extend(batch.failures)
        if not batch.items:
            continue

        try:
            inserted = storage.upsert_raw_items(batch.items)
        except Exception as error:
            failures.append(
                CollectionFailure(collector.name, "persistence", str(error))
            )
            continue

        collected_items.extend(batch.items)
        for item, is_new in zip(batch.items, inserted, strict=True):
            source_stats = stats.setdefault(item.source, [0, 0, 0])
            source_stats[0] += 1
            source_stats[1 if is_new else 2] += 1

    finished_at = clock()
    if failures and collected_items:
        status = "partial"
    elif failures:
        status = "failed"
    else:
        status = "completed"

    error_message = (
        "\n".join(
            f"{failure.source}/{failure.context}: {failure.error}"
            for failure in failures
        )
        or None
    )
    final_record = RunRecord(
        id=record_id,
        started_at=started_at,
        finished_at=finished_at,
        status=status,
        error_message=error_message,
    )
    storage.save_run_record(final_record)

    source_stats = tuple(
        SourceStats(source, values[0], values[1], values[2])
        for source, values in sorted(stats.items())
    )
    # Filtering is deliberately derived after raw persistence. Shadow mode returns
    # all items unchanged and cannot affect storage or collector behavior.
    filter_report = evaluate_in_shadow(collected_items)
    return DiscoveryResult(
        run_record=final_record,
        items=tuple(collected_items),
        source_stats=source_stats,
        failures=tuple(failures),
        filter_report=filter_report,
    )
