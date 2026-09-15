"""Generic RSS and Atom collector configured with a list of feeds."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse
from xml.etree import ElementTree

from innovation_radar.collectors.base import CollectionBatch, CollectionFailure
from innovation_radar.collectors.http import HttpClient
from innovation_radar.config import FeedConfig
from innovation_radar.models import RawItem
from innovation_radar.normalization.text import html_to_text


BytesFetcher = Callable[[str], bytes]


class RssCollector:
    """Collect multiple configured RSS/Atom feeds without site-specific code."""

    name = "rss"

    def __init__(
        self,
        feeds: tuple[FeedConfig, ...],
        limit_per_feed: int,
        get_bytes: BytesFetcher | None = None,
    ) -> None:
        if limit_per_feed < 1:
            raise ValueError("limit_per_feed must be positive")
        self.feeds = feeds
        self.limit_per_feed = limit_per_feed
        self._get_bytes = get_bytes or HttpClient().get_bytes

    def collect(self, collected_at: datetime) -> CollectionBatch:
        items: list[RawItem] = []
        failures: list[CollectionFailure] = []

        for feed in self.feeds:
            try:
                payload = self._get_bytes(feed.url)
                feed_items, feed_failures = parse_feed(
                    payload,
                    feed=feed,
                    collected_at=collected_at,
                    limit=self.limit_per_feed,
                )
                items.extend(feed_items)
                failures.extend(feed_failures)
            except Exception as error:
                failures.append(
                    CollectionFailure(self.name, f"feed:{feed.id}", str(error))
                )

        return CollectionBatch(tuple(items), tuple(failures))


def parse_feed(
    payload: bytes,
    feed: FeedConfig,
    collected_at: datetime,
    limit: int,
) -> tuple[list[RawItem], list[CollectionFailure]]:
    """Parse a bounded RSS/Atom payload into the shared RawItem model."""

    root = ElementTree.fromstring(payload)
    root_name = _local_name(root.tag)
    normalized_root_name = root_name.lower()
    if normalized_root_name not in {"rss", "rdf", "feed"}:
        raise ValueError(f"unsupported feed root element: {root_name}")
    entry_name = "entry" if normalized_root_name == "feed" else "item"
    entries = [element for element in root.iter() if _local_name(element.tag) == entry_name]

    items: list[RawItem] = []
    failures: list[CollectionFailure] = []
    for index, entry in enumerate(entries[:limit]):
        try:
            items.append(
                _parse_entry(
                    entry,
                    feed,
                    collected_at,
                    normalized_root_name == "feed",
                )
            )
        except Exception as error:
            failures.append(
                CollectionFailure(
                    "rss", f"feed:{feed.id}:entry:{index}", str(error)
                )
            )
    return items, failures


def _parse_entry(
    entry: ElementTree.Element,
    feed: FeedConfig,
    collected_at: datetime,
    is_atom: bool,
) -> RawItem:
    title = _first_text(entry, ("title",))
    if title is None:
        raise ValueError("entry title is missing")

    link = _atom_link(entry) if is_atom else _first_text(entry, ("link",))
    identifier = _first_text(entry, ("id", "guid")) or link
    if identifier is None:
        raise ValueError("entry has no stable id or link")
    identifier = identifier.strip()

    if link is None:
        parsed_identifier = urlparse(identifier)
        if parsed_identifier.scheme in {"http", "https"} and parsed_identifier.netloc:
            link = identifier
        else:
            raise ValueError("entry URL is missing")

    description = html_to_text(
        _first_text(entry, ("summary", "description", "encoded", "content"))
    )
    author = _entry_author(entry)
    published_at = _parse_datetime(
        _first_text(entry, ("published", "pubDate", "updated", "date"))
    )
    source_item_id = f"{feed.id}:{identifier}"

    return RawItem(
        id=f"rss:{source_item_id}",
        source="rss",
        source_item_id=source_item_id,
        title=title,
        description=description,
        url=link,
        author=author,
        published_at=published_at,
        first_seen_at=collected_at,
        collected_at=collected_at,
        raw_metrics={},
        raw_payload={
            "feed": {
                "id": feed.id,
                "name": feed.name,
                "url": feed.url,
                "category": feed.category,
            },
            "entry_xml": ElementTree.tostring(entry, encoding="unicode"),
        },
    )


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].rsplit(":", 1)[-1]


def _element_text(element: ElementTree.Element) -> str | None:
    text = " ".join("".join(element.itertext()).split())
    return text or None


def _first_text(
    element: ElementTree.Element, local_names: tuple[str, ...]
) -> str | None:
    wanted = set(local_names)
    for child in element:
        if _local_name(child.tag) in wanted:
            text = _element_text(child)
            if text:
                return text
    return None


def _atom_link(entry: ElementTree.Element) -> str | None:
    fallback = None
    for child in entry:
        if _local_name(child.tag) != "link":
            continue
        href = child.attrib.get("href")
        if not href:
            continue
        fallback = fallback or href
        if child.attrib.get("rel", "alternate") == "alternate":
            return href
    return fallback


def _entry_author(entry: ElementTree.Element) -> str | None:
    direct_author = _first_text(entry, ("creator", "author"))
    if direct_author:
        return direct_author
    for child in entry:
        if _local_name(child.tag) == "author":
            return _first_text(child, ("name",))
    return None


def _parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
