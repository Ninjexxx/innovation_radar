import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse

from innovation_radar.collectors.http import HttpJsonResponse
from innovation_radar.collectors.reddit import (
    RedditCollector,
    build_search_url,
    parse_reddit_post,
)
from innovation_radar.config import RedditLens
from innovation_radar.pipeline import run_discovery
from innovation_radar.storage.sqlite import SQLiteStorage


FIXTURES = Path(__file__).parent / "fixtures"
TIMESTAMP = datetime(2026, 8, 27, 15, 0, tzinfo=timezone.utc)
USER_AGENT = "windows:namu-opportunity-radar:v0.1 (by /u/approved_app_user)"


def _listing() -> dict:
    return json.loads(
        (FIXTURES / "reddit_listing_response.json").read_text(encoding="utf-8")
    )


def _lens(lens_id: str, *subreddits: str) -> RedditLens:
    return RedditLens(
        id=lens_id,
        description=f"Controlled {lens_id} lens",
        queries=('"I built"', '"I wish"'),
        subreddits=subreddits or ("QuantifiedSelf",),
    )


def test_reddit_payload_is_normalized_with_stable_post_identity() -> None:
    payload = _listing()["data"]["children"][0]["data"]

    item = parse_reddit_post(
        payload,
        collected_at=TIMESTAMP,
        discovery_contexts=(
            {
                "surface": "search_new",
                "lens": "personal_health_behavior",
                "subreddit": "QuantifiedSelf",
            },
        ),
    )

    assert item.id == "reddit:abc123"
    assert item.source == "reddit"
    assert item.source_item_id == "abc123"
    assert item.url == (
        "https://www.reddit.com/r/QuantifiedSelf/comments/abc123/"
        "local_health_dashboard/"
    )
    assert item.author == "public_fixture_user"
    assert item.published_at == datetime(2026, 8, 27, 12, 0, tzinfo=timezone.utc)
    assert item.raw_metrics == {
        "score": 2,
        "comments": 3,
        "subreddit": "QuantifiedSelf",
        "flair": "Project",
    }
    assert item.raw_payload["discovery_lenses"] == ["personal_health_behavior"]
    assert item.raw_payload["privacy"] == {
        "profile_enriched": False,
        "comments_collected": False,
        "body_excerpt_limit": 2000,
    }
    assert "author_fullname" not in item.raw_payload["post"]


def test_search_is_recent_and_never_sorted_by_popularity() -> None:
    url = build_search_url(
        _lens("unmet_needs", "caregiving"),
        "caregiving",
        limit=8,
        recency_days=30,
    )
    query = parse_qs(urlparse(url).query)

    assert urlparse(url).path == "/r/caregiving/search"
    assert query["restrict_sr"] == ["true"]
    assert query["sort"] == ["new"]
    assert query["t"] == ["month"]
    assert query["limit"] == ["8"]
    assert "top" not in query["sort"]


def test_same_post_across_lenses_and_surfaces_is_not_duplicated() -> None:
    calls: list[tuple[str, dict[str, str]]] = []

    def get_json(url: str, headers: dict[str, str]) -> HttpJsonResponse:
        calls.append((url, dict(headers)))
        return HttpJsonResponse(
            _listing(),
            {
                "X-Ratelimit-Used": "3",
                "X-Ratelimit-Remaining": "97",
                "X-Ratelimit-Reset": "42",
            },
        )

    collector = RedditCollector(
        (
            _lens("personal_health_behavior", "QuantifiedSelf"),
            _lens("unmet_needs", "QuantifiedSelf"),
        ),
        limit_per_lens=2,
        recency_days=30,
        new_limit_per_subreddit=1,
        user_agent=USER_AGENT,
        token_provider=lambda: "fixture-token",
        get_json=get_json,
    )

    batch = collector.collect(TIMESTAMP)

    assert not batch.failures
    assert [item.source_item_id for item in batch.items] == ["abc123", "def456"]
    assert len({item.id for item in batch.items}) == 2
    assert batch.items[0].raw_payload["discovery_lenses"] == [
        "personal_health_behavior",
        "unmet_needs",
    ]
    assert collector.collection_stats.requests == 3
    assert collector.collection_stats.unique_candidates == 2
    assert collector.collection_stats.duplicates_avoided == 6
    assert collector.collection_stats.outside_time_window == 4
    assert collector.rate_limits[-1].remaining == "97"
    assert all(headers["Authorization"] == "Bearer fixture-token" for _, headers in calls)
    assert all(headers["User-Agent"] == USER_AGENT for _, headers in calls)
    assert any(urlparse(url).path.endswith("/new") for url, _ in calls)
    assert any(urlparse(url).path.endswith("/search") for url, _ in calls)


def test_production_oauth_uses_client_credentials_and_identified_user_agent() -> None:
    class StubHttpClient:
        def __init__(self) -> None:
            self.token_call: tuple[str, dict[str, str], dict[str, str]] | None = None

        def post_form_json_response(
            self, url: str, form: dict[str, str], headers: dict[str, str]
        ) -> HttpJsonResponse:
            self.token_call = (url, dict(form), dict(headers))
            return HttpJsonResponse(
                {"access_token": "approved-token", "token_type": "bearer"}, {}
            )

        def get_json_response(
            self, url: str, headers: dict[str, str]
        ) -> HttpJsonResponse:
            assert headers["Authorization"] == "Bearer approved-token"
            return HttpJsonResponse(_listing(), {})

    http_client = StubHttpClient()
    collector = RedditCollector(
        (_lens("personal_health_behavior", "QuantifiedSelf"),),
        limit_per_lens=2,
        recency_days=30,
        client_id="approved-client",
        client_secret="approved-secret",
        user_agent=USER_AGENT,
        http_client=http_client,  # type: ignore[arg-type]
    )

    batch = collector.collect(TIMESTAMP)

    assert len(batch.items) == 2
    assert http_client.token_call is not None
    token_url, form, headers = http_client.token_call
    assert token_url.endswith("/api/v1/access_token")
    assert form == {"grant_type": "client_credentials"}
    assert headers["Authorization"].startswith("Basic ")
    assert headers["User-Agent"] == USER_AGENT
    assert "approved-secret" not in str(batch.items)


def test_reddit_collector_enters_pipeline_and_reencounter_updates_one_row(
    tmp_path: Path,
) -> None:
    collector = RedditCollector(
        (_lens("personal_health_behavior", "QuantifiedSelf"),),
        limit_per_lens=2,
        recency_days=30,
        user_agent=USER_AGENT,
        token_provider=lambda: "fixture-token",
        get_json=lambda url, headers: _listing(),
    )
    storage = SQLiteStorage(tmp_path / "radar.sqlite3")

    first = run_discovery(
        storage,
        (collector,),
        clock=lambda: TIMESTAMP,
        run_id="reddit-first",
    )
    second = run_discovery(
        storage,
        (collector,),
        clock=lambda: datetime(2026, 8, 27, 16, 0, tzinfo=timezone.utc),
        run_id="reddit-second",
    )

    assert first.total == 2
    assert first.new_count == 2
    assert second.total == 2
    assert second.updated_count == 2
    assert storage.count_raw_items() == 2


def test_missing_approved_oauth_configuration_fails_clearly() -> None:
    collector = RedditCollector(
        (_lens("unmet_needs", "caregiving"),),
        limit_per_lens=2,
        recency_days=30,
    )

    batch = collector.collect(TIMESTAMP)

    assert not batch.items
    assert len(batch.failures) == 1
    assert batch.failures[0].context == "authentication"
    assert "approved OAuth client" in batch.failures[0].error


def test_denied_api_access_stops_without_fragile_fallback() -> None:
    calls = 0

    def denied(url: str, headers: dict[str, str]) -> dict:
        nonlocal calls
        calls += 1
        raise HTTPError(url, 403, "Forbidden", hdrs=None, fp=None)

    collector = RedditCollector(
        (_lens("unmet_needs", "caregiving", "disability"),),
        limit_per_lens=2,
        recency_days=30,
        user_agent=USER_AGENT,
        token_provider=lambda: "fixture-token",
        get_json=denied,
    )

    batch = collector.collect(TIMESTAMP)

    assert not batch.items
    assert calls == 1
    assert len(batch.failures) == 1
    assert "access denied" in batch.failures[0].error
    assert "approval" in batch.failures[0].error


def test_oauth_failure_is_reported_without_exposing_credentials() -> None:
    collector = RedditCollector(
        (_lens("unmet_needs", "caregiving"),),
        limit_per_lens=2,
        recency_days=30,
        user_agent=USER_AGENT,
        token_provider=lambda: (_ for _ in ()).throw(OSError("invalid client")),
    )

    batch = collector.collect(TIMESTAMP)

    assert not batch.items
    assert batch.failures[0].context == "authentication"
    assert "OAuth access failed" in batch.failures[0].error
