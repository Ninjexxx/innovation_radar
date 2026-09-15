import csv
import os
import subprocess
import sys
from pathlib import Path

import pytest

from innovation_radar.config import REPORT_DIRECTORY_ENV
from innovation_radar.reports.review_page import (
    render_review_page,
    write_review_page,
)


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = [
        "item_id",
        "source",
        "source_surface_or_feed",
        "title",
        "url",
        "published_at",
        "author",
        "short_description",
        "available_metrics",
        "human_label",
        "human_reason",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def _row(item_id: str, **overrides: str) -> dict[str, str]:
    base = {
        "item_id": item_id,
        "source": "hacker_news",
        "source_surface_or_feed": "newstories",
        "title": f"Title {item_id}",
        "url": f"https://example.com/{item_id}",
        "published_at": "2026-08-27T13:00:00Z",
        "author": "fixture",
        "short_description": "A controlled description.",
        "available_metrics": "{\"score\":10}",
    }
    base.update(overrides)
    return base


def test_render_includes_dataset_and_item_count() -> None:
    html = render_review_page([_row("hn:1"), _row("hn:2", source="rss")])
    assert "<!DOCTYPE html>" in html
    assert "Revisão de descoberta" in html
    # Both items appear in the embedded JSON dataset.
    assert "hn:1" in html
    assert "hn:2" in html
    # Export schema includes the human columns for the downloaded CSV.
    assert "human_label" in html
    assert "human_reason" in html


def test_render_escapes_script_closing_tag_in_content() -> None:
    # Untrusted content trying to close the embedded script tag must be neutralized.
    malicious = 'evil</script><script>alert(1)</script>'
    html = render_review_page([_row("hn:x", title=malicious)])
    # The raw closing sequence must not survive verbatim inside the payload.
    assert "</script><script>alert(1)" not in html
    # It is escaped as <\/script ...>, so the injected opening tag is defanged.
    assert "<\\/script>" in html


def test_write_review_page_roundtrips(tmp_path: Path) -> None:
    csv_path = tmp_path / "review_sample.csv"
    html_path = tmp_path / "review.html"
    _write_csv(csv_path, [_row("hn:1"), _row("hn:2")])

    result = write_review_page(csv_path, html_path)

    assert result.item_count == 2
    assert html_path.is_file()
    content = html_path.read_text(encoding="utf-8")
    assert "hn:1" in content and "hn:2" in content


def test_write_review_page_rejects_empty_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "review_sample.csv"
    _write_csv(csv_path, [])
    with pytest.raises(ValueError):
        write_review_page(csv_path, tmp_path / "review.html")


def test_write_review_page_missing_csv(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        write_review_page(tmp_path / "missing.csv", tmp_path / "review.html")


def test_export_review_page_cli(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    report_directory = tmp_path / "reports"
    report_directory.mkdir()
    _write_csv(report_directory / "review_sample.csv", [_row("hn:1"), _row("hn:2")])

    environment = os.environ.copy()
    environment[REPORT_DIRECTORY_ENV] = str(report_directory)
    environment["PYTHONPATH"] = str(project_root / "src")

    result = subprocess.run(
        [sys.executable, "-m", "innovation_radar", "export-review-page"],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (report_directory / "review.html").is_file()
    assert "Review page written with 2 items" in result.stderr
