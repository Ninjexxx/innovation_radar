import os
import csv
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from innovation_radar.config import (
    DATABASE_PATH_ENV,
    LOG_LEVEL_ENV,
    REPORT_DIRECTORY_ENV,
)
from innovation_radar.models import RawItem
from innovation_radar.storage.sqlite import SQLiteStorage


def test_init_db_cli(tmp_path: Path) -> None:
    database_path = tmp_path / "cli.sqlite3"
    project_root = Path(__file__).resolve().parents[1]
    source_path = project_root / "src"
    environment = os.environ.copy()
    environment[DATABASE_PATH_ENV] = str(database_path)
    environment[LOG_LEVEL_ENV] = "INFO"
    existing_pythonpath = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = os.pathsep.join(
        part for part in (str(source_path), existing_pythonpath) if part
    )

    result = subprocess.run(
        [sys.executable, "-m", "innovation_radar", "init-db"],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert database_path.is_file()
    assert "SQLite database initialized" in result.stderr


def test_export_review_sample_cli(tmp_path: Path) -> None:
    database_path = tmp_path / "cli.sqlite3"
    report_directory = tmp_path / "reports"
    storage = SQLiteStorage(database_path)
    storage.initialize()
    timestamp = datetime(2026, 8, 27, 13, 0, tzinfo=timezone.utc)
    storage.save_raw_item(
        RawItem(
            id="hacker_news:1",
            source="hacker_news",
            source_item_id="1",
            title="Reviewable item",
            url="https://example.com/item",
            first_seen_at=timestamp,
            collected_at=timestamp,
            raw_payload={"discovery_surfaces": ["newstories"]},
        )
    )

    project_root = Path(__file__).resolve().parents[1]
    environment = os.environ.copy()
    environment[DATABASE_PATH_ENV] = str(database_path)
    environment[REPORT_DIRECTORY_ENV] = str(report_directory)
    environment["PYTHONPATH"] = str(project_root / "src")

    result = subprocess.run(
        [sys.executable, "-m", "innovation_radar", "export-review-sample"],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    with (report_directory / "review_sample.csv").open(
        encoding="utf-8-sig", newline=""
    ) as csv_file:
        rows = list(csv.DictReader(csv_file))
    assert [row["item_id"] for row in rows] == ["hacker_news:1"]
    assert "Review sample exported with 1 items" in result.stderr
