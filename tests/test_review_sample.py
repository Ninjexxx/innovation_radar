import csv
from datetime import datetime, timezone
from pathlib import Path

from innovation_radar.config import REVIEW_SAMPLE_LIMIT_ENV, Settings
from innovation_radar.models import RawItem, RunRecord
from innovation_radar.reports.review_sample import CSV_FIELDS, write_review_sample
from innovation_radar.storage.sqlite import SQLiteStorage


TIMESTAMP = datetime(2026, 8, 27, 13, 0, tzinfo=timezone.utc)


def _item(
    item_id: str,
    source: str,
    detail: str,
    description: str = "A controlled description.",
) -> RawItem:
    if source == "hacker_news":
        payload = {"discovery_surfaces": [detail]}
        source_item_id = item_id
    else:
        payload = {
            "feed": {
                "id": detail,
                "name": f"Feed {detail}",
                "url": f"https://example.com/{detail}",
            }
        }
        source_item_id = f"{detail}:{item_id}"
    return RawItem(
        id=f"{source}:{source_item_id}",
        source=source,
        source_item_id=source_item_id,
        title=f"Item {item_id}",
        description=description,
        url=f"https://example.com/items/{item_id}",
        author="Reviewer fixture",
        published_at=TIMESTAMP,
        first_seen_at=TIMESTAMP,
        collected_at=TIMESTAMP,
        raw_metrics={"score": 99} if source == "hacker_news" else {},
        raw_payload=payload,
    )


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as csv_file:
        return list(csv.DictReader(csv_file))


def test_exports_reviewable_csv_with_empty_human_fields(tmp_path: Path) -> None:
    storage = SQLiteStorage(tmp_path / "radar.sqlite3")
    storage.initialize()
    storage.save_raw_item(_item("1", "hacker_news", "newstories"))

    result = write_review_sample(storage, tmp_path / "reports", limit=10)
    rows = _read_rows(result.csv_path)

    assert result.item_count == 1
    assert tuple(rows[0]) == CSV_FIELDS
    assert rows[0]["source_surface_or_feed"] == "newstories"
    assert rows[0]["available_metrics"] == '{"score":99}'
    assert rows[0]["human_label"] == ""
    assert rows[0]["human_reason"] == ""
    assert "Não contém ranking, classificação" in result.summary_path.read_text(
        encoding="utf-8"
    )


def test_review_sample_limit_is_configurable_and_enforced(tmp_path: Path) -> None:
    settings = Settings.from_env({REVIEW_SAMPLE_LIMIT_ENV: "2"})
    storage = SQLiteStorage(tmp_path / "radar.sqlite3")
    storage.initialize()
    for index in range(4):
        storage.save_raw_item(_item(str(index), "hacker_news", "newstories"))

    result = write_review_sample(
        storage, tmp_path / "reports", limit=settings.review_sample_limit
    )

    assert settings.review_sample_limit == 2
    assert result.item_count == 2
    assert len(_read_rows(result.csv_path)) == 2


def test_sample_preserves_source_and_provenance_diversity_when_available(
    tmp_path: Path,
) -> None:
    storage = SQLiteStorage(tmp_path / "radar.sqlite3")
    storage.initialize()
    items = (
        _item("1", "hacker_news", "newstories"),
        _item("2", "hacker_news", "showstories"),
        _item("3", "hacker_news", "beststories"),
        _item("4", "rss", "mit_ai"),
        _item("5", "rss", "medium_healthtech"),
    )
    storage.upsert_raw_items(items)
    storage.save_run_record(
        RunRecord(
            id="run-diverse",
            started_at=TIMESTAMP,
            finished_at=TIMESTAMP,
            status="completed",
        )
    )

    result = write_review_sample(storage, tmp_path / "reports", limit=5)
    rows = _read_rows(result.csv_path)
    details = {row["source_surface_or_feed"] for row in rows}

    assert {row["source"] for row in rows} == {"hacker_news", "rss"}
    assert {"newstories", "showstories", "beststories"} <= details
    assert "Feed mit_ai [mit_ai]" in details
    assert "Feed medium_healthtech [medium_healthtech]" in details
    summary = result.summary_path.read_text(encoding="utf-8")
    assert "Período coberto" in summary
    assert "Reencontros consolidados no SQLite na execução mais recente: **0**" in summary
    assert "Linhas duplicadas descartadas defensivamente na exportação: **0**" in summary
    assert "Nenhuma falha registrada" in summary


def test_github_review_row_includes_lenses_metadata_and_readme_excerpt(
    tmp_path: Path,
) -> None:
    storage = SQLiteStorage(tmp_path / "radar.sqlite3")
    storage.initialize()
    storage.save_raw_item(
        RawItem(
            id="github:101",
            source="github",
            source_item_id="101",
            title="example-health/pulse-lab",
            description="A wearable recovery experiment.",
            url="https://github.com/example-health/pulse-lab",
            author="example-health",
            published_at=TIMESTAMP,
            first_seen_at=TIMESTAMP,
            collected_at=TIMESTAMP,
            raw_metrics={
                "stars": 3,
                "forks": 1,
                "language": "Python",
                "topics": ["wearable", "personal-data"],
                "updated_at": "2026-08-25T11:00:00Z",
                "pushed_at": "2026-08-24T17:30:00Z",
            },
            raw_payload={
                "discovery_lenses": ["wearables_sensors", "personal_data"],
                "readme": {
                    "source_url": "https://api.github.com/repos/example-health/pulse-lab/readme",
                    "excerpt": "A small, testable wearable prototype.",
                },
            },
        )
    )

    result = write_review_sample(storage, tmp_path / "reports", limit=10)
    row = _read_rows(result.csv_path)[0]

    assert row["source_surface_or_feed"] == "wearables_sensors | personal_data"
    assert row["title"] == "example-health/pulse-lab"
    assert row["author"] == "example-health"
    assert "README: A small, testable wearable prototype." in row["short_description"]
    assert '"language":"Python"' in row["available_metrics"]
    assert '"stars":3' in row["available_metrics"]
    assert row["human_label"] == ""
    assert row["human_reason"] == ""


def test_reddit_review_row_includes_subreddit_lenses_and_public_metrics(
    tmp_path: Path,
) -> None:
    storage = SQLiteStorage(tmp_path / "radar.sqlite3")
    storage.initialize()
    storage.save_raw_item(
        RawItem(
            id="reddit:abc123",
            source="reddit",
            source_item_id="abc123",
            title="I built a private health dashboard",
            description="A public excerpt explaining the personal experiment.",
            url="https://www.reddit.com/r/QuantifiedSelf/comments/abc123/example/",
            author="public_fixture_user",
            published_at=TIMESTAMP,
            first_seen_at=TIMESTAMP,
            collected_at=TIMESTAMP,
            raw_metrics={
                "score": 2,
                "comments": 3,
                "subreddit": "QuantifiedSelf",
                "flair": "Project",
            },
            raw_payload={
                "post": {"subreddit": "QuantifiedSelf"},
                "discovery_lenses": [
                    "personal_health_behavior",
                    "personal_data_and_automation",
                ],
            },
        )
    )

    result = write_review_sample(storage, tmp_path / "reports", limit=10)
    row = _read_rows(result.csv_path)[0]
    summary = result.summary_path.read_text(encoding="utf-8")

    assert row["source_surface_or_feed"] == (
        "r/QuantifiedSelf | lens:personal_health_behavior | "
        "lens:personal_data_and_automation"
    )
    assert row["short_description"] == (
        "A public excerpt explaining the personal experiment."
    )
    assert row["author"] == "public_fixture_user"
    assert '"comments":3' in row["available_metrics"]
    assert '"score":2' in row["available_metrics"]
    assert row["human_label"] == ""
    assert row["human_reason"] == ""
    assert "Reddit por discovery lens" in summary
    assert "Reddit por subreddit" in summary
    assert "personal_health_behavior" in summary
    assert "r/QuantifiedSelf" in summary
