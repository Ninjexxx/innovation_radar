import csv
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from innovation_radar.config import DATABASE_PATH_ENV, REPORT_DIRECTORY_ENV
from innovation_radar.models import ItemReview, RawItem
from innovation_radar.reports.review_sample import write_review_sample
from innovation_radar.reviews.ingest import ingest_reviewed_csv
from innovation_radar.storage.sqlite import SQLiteStorage


NOW = datetime(2026, 9, 15, 12, tzinfo=timezone.utc)


def _item(item_id: str, surface: str = "newstories") -> RawItem:
    return RawItem(
        id=f"hacker_news:{item_id}",
        source="hacker_news",
        source_item_id=item_id,
        title=f"Title {item_id}",
        url=f"https://example.com/{item_id}",
        description="A controlled description.",
        first_seen_at=NOW,
        collected_at=NOW,
        raw_payload={"discovery_surfaces": [surface]},
    )


def _labeled_csv(path: Path, rows: list[tuple[str, str, str]]) -> None:
    fields = ["item_id", "human_label", "human_reason"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item_id, label, reason in rows:
            writer.writerow(
                {"item_id": item_id, "human_label": label, "human_reason": reason}
            )


# --- storage ---------------------------------------------------------------


def test_storage_saves_and_lists_reviews(tmp_path: Path) -> None:
    storage = SQLiteStorage(tmp_path / "db.sqlite3")
    storage.initialize()
    count = storage.save_reviews(
        [
            ItemReview("hacker_news:1", "irrelevant", NOW, "noise"),
            ItemReview("hacker_news:2", "maybe", NOW, None),
        ]
    )
    assert count == 2
    assert storage.reviewed_item_ids() == {"hacker_news:1", "hacker_news:2"}
    assert storage.count_reviews() == 2


def test_storage_review_upsert_is_idempotent(tmp_path: Path) -> None:
    storage = SQLiteStorage(tmp_path / "db.sqlite3")
    storage.initialize()
    storage.save_reviews([ItemReview("hacker_news:1", "maybe", NOW)])
    storage.save_reviews([ItemReview("hacker_news:1", "interesting", NOW)])
    assert storage.count_reviews() == 1


# --- ingestion -------------------------------------------------------------


def test_ingest_reads_labels_and_skips_blank(tmp_path: Path) -> None:
    csv_path = tmp_path / "labeled.csv"
    _labeled_csv(
        csv_path,
        [
            ("hacker_news:1", "irrelevant", "noise"),
            ("hacker_news:2", "", ""),  # not yet decided -> skipped
            ("hacker_news:3", "interesting", "good"),
        ],
    )
    storage = SQLiteStorage(tmp_path / "db.sqlite3")
    result = ingest_reviewed_csv(csv_path, storage)
    assert result.ingested_count == 2
    assert result.skipped_unlabeled_count == 1
    assert storage.reviewed_item_ids() == {"hacker_news:1", "hacker_news:3"}


def test_ingest_rejects_invalid_label(tmp_path: Path) -> None:
    csv_path = tmp_path / "labeled.csv"
    _labeled_csv(csv_path, [("hacker_news:1", "amazing", "x")])
    storage = SQLiteStorage(tmp_path / "db.sqlite3")
    with pytest.raises(ValueError):
        ingest_reviewed_csv(csv_path, storage)


def test_ingest_rejects_duplicate_item_id(tmp_path: Path) -> None:
    csv_path = tmp_path / "labeled.csv"
    _labeled_csv(
        csv_path,
        [("hacker_news:1", "maybe", "a"), ("hacker_news:1", "irrelevant", "b")],
    )
    storage = SQLiteStorage(tmp_path / "db.sqlite3")
    with pytest.raises(ValueError):
        ingest_reviewed_csv(csv_path, storage)


# --- sample excludes reviewed ---------------------------------------------


def test_sample_excludes_reviewed_items(tmp_path: Path) -> None:
    storage = SQLiteStorage(tmp_path / "db.sqlite3")
    storage.initialize()
    storage.upsert_raw_items([_item(str(n)) for n in range(1, 6)])

    first = write_review_sample(storage, tmp_path / "r1", limit=2)
    first_ids = [row["item_id"] for row in _read_csv(first.csv_path)]
    assert len(first_ids) == 2

    # Mark the first batch as reviewed, then export again.
    storage.save_reviews(
        [ItemReview(item_id, "irrelevant", NOW) for item_id in first_ids]
    )
    second = write_review_sample(storage, tmp_path / "r2", limit=2)
    second_ids = [row["item_id"] for row in _read_csv(second.csv_path)]

    assert second.already_reviewed_skipped == 2
    assert set(first_ids).isdisjoint(second_ids)  # no repeats


def test_sample_raises_when_all_reviewed(tmp_path: Path) -> None:
    storage = SQLiteStorage(tmp_path / "db.sqlite3")
    storage.initialize()
    storage.upsert_raw_items([_item("1"), _item("2")])
    storage.save_reviews(
        [ItemReview("hacker_news:1", "irrelevant", NOW), ItemReview("hacker_news:2", "maybe", NOW)]
    )
    with pytest.raises(ValueError):
        write_review_sample(storage, tmp_path / "r", limit=2)


# --- CLI end-to-end --------------------------------------------------------


def test_mark_reviewed_cli_prevents_repeats(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    database_path = tmp_path / "db.sqlite3"
    report_dir = tmp_path / "reports"

    storage = SQLiteStorage(database_path)
    storage.initialize()
    storage.upsert_raw_items([_item(str(n)) for n in range(1, 6)])

    # First export (via API to get the ids), then mark them reviewed via CLI.
    first = write_review_sample(storage, report_dir, limit=2)
    first_ids = [row["item_id"] for row in _read_csv(first.csv_path)]
    labeled = tmp_path / "labeled.csv"
    _labeled_csv(labeled, [(item_id, "irrelevant", "seen") for item_id in first_ids])

    environment = os.environ.copy()
    environment[DATABASE_PATH_ENV] = str(database_path)
    environment[REPORT_DIRECTORY_ENV] = str(report_dir)
    environment["PYTHONPATH"] = str(project_root / "src")

    marked = subprocess.run(
        [sys.executable, "-m", "innovation_radar", "mark-reviewed", str(labeled)],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert marked.returncode == 0, marked.stderr
    assert "Recorded 2 reviewed items" in marked.stderr

    # Next export must not contain the reviewed ids.
    second = write_review_sample(storage, report_dir, limit=2)
    second_ids = [row["item_id"] for row in _read_csv(second.csv_path)]
    assert set(first_ids).isdisjoint(second_ids)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))
