"""Collector for public Hacker News discovery surfaces."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from typing import Any

from innovation_radar.collectors.base import CollectionBatch, CollectionFailure
from innovation_radar.collectors.http import HttpClient
from innovation_radar.models import RawItem
from innovation_radar.normalization.text import html_to_text


API_BASE_URL = "https://hacker-news.firebaseio.com/v0"
DISCOVERY_SURFACES = ("newstories", "showstories", "beststories")
JsonFetcher = Callable[[str], Any]


class HackerNewsCollector:
    """Collect a bounded sample of new, Show HN, and best stories."""

    name = "hacker_news"

    def __init__(
        self,
        limit_per_surface: int,
        get_json: JsonFetcher | None = None,
    ) -> None:
        if limit_per_surface < 1:
            raise ValueError("limit_per_surface must be positive")
        self.limit_per_surface = limit_per_surface
        self._get_json = get_json or HttpClient().get_json

    def collect(self, collected_at: datetime) -> CollectionBatch:
        ordered_ids: list[int] = []
        item_surfaces: dict[int, list[str]] = {}
        failures: list[CollectionFailure] = []

        for surface in DISCOVERY_SURFACES:
            try:
                payload = self._get_json(f"{API_BASE_URL}/{surface}.json")
                if not isinstance(payload, list):
                    raise ValueError("surface response must be a JSON array")
            except Exception as error:
                failures.append(
                    CollectionFailure(self.name, f"surface:{surface}", str(error))
                )
                continue

            for raw_item_id in payload[: self.limit_per_surface]:
                if not isinstance(raw_item_id, int) or isinstance(raw_item_id, bool):
                    failures.append(
                        CollectionFailure(
                            self.name,
                            f"surface:{surface}",
                            f"invalid item id: {raw_item_id!r}",
                        )
                    )
                    continue
                if raw_item_id not in item_surfaces:
                    ordered_ids.append(raw_item_id)
                    item_surfaces[raw_item_id] = []
                item_surfaces[raw_item_id].append(surface)

        items: list[RawItem] = []
        for item_id in ordered_ids:
            try:
                payload = self._get_json(f"{API_BASE_URL}/item/{item_id}.json")
                if not isinstance(payload, Mapping):
                    raise ValueError("item response must be a JSON object")
                items.append(
                    parse_hackernews_item(
                        payload,
                        collected_at=collected_at,
                        discovery_surfaces=tuple(item_surfaces[item_id]),
                    )
                )
            except Exception as error:
                failures.append(
                    CollectionFailure(self.name, f"item:{item_id}", str(error))
                )

        return CollectionBatch(tuple(items), tuple(failures))


def parse_hackernews_item(
    payload: Mapping[str, Any],
    collected_at: datetime,
    discovery_surfaces: tuple[str, ...],
) -> RawItem:
    """Normalize one official HN item payload without judging its relevance."""

    if payload.get("deleted") or payload.get("dead"):
        raise ValueError("item is deleted or dead")

    item_id = payload.get("id")
    if not isinstance(item_id, int) or isinstance(item_id, bool):
        raise ValueError("item id is missing or invalid")
    title = payload.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("item title is missing")

    external_url = payload.get("url")
    url = (
        external_url.strip()
        if isinstance(external_url, str) and external_url.strip()
        else f"https://news.ycombinator.com/item?id={item_id}"
    )
    author = payload.get("by") if isinstance(payload.get("by"), str) else None
    description = html_to_text(
        payload.get("text") if isinstance(payload.get("text"), str) else None
    )

    published_at = None
    raw_timestamp = payload.get("time")
    if isinstance(raw_timestamp, (int, float)) and not isinstance(raw_timestamp, bool):
        published_at = datetime.fromtimestamp(raw_timestamp, tz=timezone.utc)

    raw_metrics: dict[str, int] = {}
    score = payload.get("score")
    if isinstance(score, int) and not isinstance(score, bool):
        raw_metrics["score"] = score
    descendants = payload.get("descendants")
    if isinstance(descendants, int) and not isinstance(descendants, bool):
        raw_metrics["comments"] = descendants

    source_item_id = str(item_id)
    return RawItem(
        id=f"hacker_news:{source_item_id}",
        source="hacker_news",
        source_item_id=source_item_id,
        title=title,
        description=description,
        url=url,
        author=author,
        published_at=published_at,
        first_seen_at=collected_at,
        collected_at=collected_at,
        raw_metrics=raw_metrics,
        raw_payload={
            "item": dict(payload),
            "discovery_surfaces": list(discovery_surfaces),
        },
    )
