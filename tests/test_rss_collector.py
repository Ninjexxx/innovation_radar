from datetime import datetime, timezone
from pathlib import Path

from innovation_radar.collectors.rss import RssCollector
from innovation_radar.config import FeedConfig
from innovation_radar.models import RawItem


FIXTURES = Path(__file__).parent / "fixtures"


def test_parses_rss_and_atom_into_shared_model() -> None:
    feeds = (
        FeedConfig(
            id="rss_validation",
            name="RSS validation",
            url="https://example.com/rss",
            category="health",
        ),
        FeedConfig(
            id="atom_validation",
            name="Atom validation",
            url="https://example.com/atom",
        ),
    )
    payloads = {
        feeds[0].url: (FIXTURES / "rss_feed.xml").read_bytes(),
        feeds[1].url: (FIXTURES / "atom_feed.xml").read_bytes(),
    }
    collected_at = datetime(2026, 8, 27, 13, 0, tzinfo=timezone.utc)

    batch = RssCollector(
        feeds,
        limit_per_feed=10,
        get_bytes=lambda url: payloads[url],
    ).collect(collected_at)

    assert not batch.failures
    assert len(batch.items) == 3
    assert all(isinstance(item, RawItem) for item in batch.items)

    rss_item = batch.items[0]
    assert rss_item.source == "rss"
    assert rss_item.source_item_id == "rss_validation:rss-item-1"
    assert rss_item.description == "An original summary."
    assert rss_item.author == "RSS Author"
    assert rss_item.raw_payload["feed"]["category"] == "health"
    assert rss_item.raw_payload["feed"]["id"] == "rss_validation"
    assert rss_item.raw_payload["feed"]["name"] == "RSS validation"

    assert batch.items[1].url == "https://example.com/rss/item-2"
    atom_item = batch.items[2]
    assert atom_item.author == "Atom Author"
    assert atom_item.description == "A controlled Atom summary."
    assert atom_item.published_at == datetime(
        2026, 8, 27, 12, 10, tzinfo=timezone.utc
    )


def test_rss_feed_failure_does_not_discard_successful_feed() -> None:
    working = FeedConfig("working", "Working", "https://example.com/working")
    unavailable = FeedConfig(
        "unavailable", "Unavailable", "https://example.com/unavailable"
    )
    payload = (FIXTURES / "rss_feed.xml").read_bytes()

    def get_bytes(url: str) -> bytes:
        if url == unavailable.url:
            raise OSError("feed unavailable")
        return payload

    batch = RssCollector(
        (working, unavailable), limit_per_feed=1, get_bytes=get_bytes
    ).collect(datetime(2026, 8, 27, 13, 0, tzinfo=timezone.utc))

    assert len(batch.items) == 1
    assert len(batch.failures) == 1
    assert batch.failures[0].context == "feed:unavailable"


def test_rss_rejects_non_feed_xml_clearly() -> None:
    feed = FeedConfig("invalid", "Invalid", "https://example.com/not-a-feed")

    batch = RssCollector(
        (feed,),
        limit_per_feed=1,
        get_bytes=lambda url: b"<html><body>not a feed</body></html>",
    ).collect(datetime(2026, 8, 27, 13, 0, tzinfo=timezone.utc))

    assert not batch.items
    assert len(batch.failures) == 1
    assert "unsupported feed root element" in batch.failures[0].error


def test_feed_display_name_does_not_change_item_identity() -> None:
    payload = (FIXTURES / "rss_feed.xml").read_bytes()
    collected_at = datetime(2026, 8, 27, 13, 0, tzinfo=timezone.utc)
    original = FeedConfig(
        id="stable_feed",
        name="Original display name",
        url="https://example.com/rss",
    )
    renamed = FeedConfig(
        id="stable_feed",
        name="Renamed display name",
        url="https://example.com/rss",
    )

    original_item = RssCollector(
        (original,), 1, get_bytes=lambda url: payload
    ).collect(collected_at).items[0]
    renamed_item = RssCollector(
        (renamed,), 1, get_bytes=lambda url: payload
    ).collect(collected_at).items[0]

    assert original_item.id == renamed_item.id
    assert original_item.source_item_id == renamed_item.source_item_id
    assert original_item.raw_payload["feed"]["name"] != renamed_item.raw_payload["feed"]["name"]
