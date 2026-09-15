import json
from datetime import datetime, timezone
from pathlib import Path

from innovation_radar.collectors.hackernews import API_BASE_URL, HackerNewsCollector
from innovation_radar.models import RawItem


def test_parses_and_normalizes_hacker_news_surfaces() -> None:
    fixture_path = Path(__file__).parent / "fixtures" / "hackernews_payloads.json"
    payloads = json.loads(fixture_path.read_text(encoding="utf-8"))

    def get_json(url: str):
        return payloads[url.removeprefix(API_BASE_URL)]

    collected_at = datetime(2026, 8, 27, 13, 0, tzinfo=timezone.utc)
    batch = HackerNewsCollector(limit_per_surface=2, get_json=get_json).collect(
        collected_at
    )

    assert not batch.failures
    assert all(isinstance(item, RawItem) for item in batch.items)
    assert [item.source_item_id for item in batch.items] == ["101", "102", "103", "104"]

    show_item = batch.items[1]
    assert show_item.source == "hacker_news"
    assert show_item.description == "A small working prototype."
    assert show_item.url == "https://news.ycombinator.com/item?id=102"
    assert show_item.raw_metrics == {"score": 5, "comments": 3}
    assert show_item.raw_payload["discovery_surfaces"] == [
        "newstories",
        "showstories",
    ]

    # The high-popularity complementary item remains last; no metric ranking occurs.
    assert batch.items[-1].raw_metrics["score"] == 999
