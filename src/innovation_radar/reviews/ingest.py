"""Ingest a human-labeled review CSV into the SQLite review memory.

This closes the daily loop: after a person marks items in the review page and
downloads ``review_sample_labeled.csv``, this module reads that file, validates
the labels, and records each decision so the item is never shown again.

It performs no interpretation of content. It only trusts the human label and
stores it. Rows left unlabeled are skipped (not yet decided), not errored.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from innovation_radar.models import ItemReview
from innovation_radar.storage.sqlite import SQLiteStorage


ALLOWED_LABELS = frozenset({"interesting", "maybe", "irrelevant"})


@dataclass(frozen=True, slots=True)
class ReviewIngestResult:
    ingested_count: int
    skipped_unlabeled_count: int


def ingest_reviewed_csv(
    csv_path: str | Path,
    storage: SQLiteStorage,
    *,
    now: datetime | None = None,
) -> ReviewIngestResult:
    """Read a labeled review CSV and persist its decisions into review memory."""

    source_path = Path(csv_path)
    reviewed_at = now or datetime.now(timezone.utc)
    reviews: list[ItemReview] = []
    skipped_unlabeled = 0
    seen_ids: set[str] = set()

    try:
        with source_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None or "item_id" not in reader.fieldnames:
                raise ValueError("review CSV must have an item_id column")
            if "human_label" not in reader.fieldnames:
                raise ValueError("review CSV must have a human_label column")
            for index, row in enumerate(reader, start=1):
                item_id = (row.get("item_id") or "").strip()
                if not item_id:
                    raise ValueError(f"row {index} has an empty item_id")
                label = (row.get("human_label") or "").strip().lower()
                if not label:
                    skipped_unlabeled += 1
                    continue
                if label not in ALLOWED_LABELS:
                    raise ValueError(
                        f"row {index} has invalid human_label {label!r}; "
                        f"expected one of {sorted(ALLOWED_LABELS)}"
                    )
                if item_id in seen_ids:
                    raise ValueError(f"row {index} duplicates item_id {item_id!r}")
                seen_ids.add(item_id)
                reason = (row.get("human_reason") or "").strip() or None
                reviews.append(
                    ItemReview(
                        item_id=item_id,
                        human_label=label,
                        human_reason=reason,
                        reviewed_at=reviewed_at,
                    )
                )
    except OSError as error:
        raise ValueError(
            f"review CSV is not readable: {source_path}: {error}"
        ) from error

    storage.initialize()
    ingested = storage.save_reviews(reviews)
    return ReviewIngestResult(
        ingested_count=ingested,
        skipped_unlabeled_count=skipped_unlabeled,
    )
