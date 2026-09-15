import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from innovation_radar.collectors.github import (
    API_VERSION,
    GitHubCollector,
    parse_github_repository,
)
from innovation_radar.collectors.http import HttpJsonResponse
from innovation_radar.config import GitHubLens
from innovation_radar.pipeline import run_discovery
from innovation_radar.storage.sqlite import SQLiteStorage


FIXTURES = Path(__file__).parent / "fixtures"
TIMESTAMP = datetime(2026, 8, 27, 15, 0, tzinfo=timezone.utc)


def _search_payload() -> dict:
    return json.loads(
        (FIXTURES / "github_search_response.json").read_text(encoding="utf-8")
    )


def _readme_payload() -> dict:
    return json.loads(
        (FIXTURES / "github_readme_response.json").read_text(encoding="utf-8")
    )


def _lens(lens_id: str = "wearables") -> GitHubLens:
    return GitHubLens(
        id=lens_id,
        description=f"Fixture lens {lens_id}",
        query=f'"{lens_id}" OR experiment',
    )


def test_api_payload_is_normalized_with_repository_metadata() -> None:
    payload = _search_payload()["items"][0]

    item = parse_github_repository(
        payload,
        collected_at=TIMESTAMP,
        discovery_contexts=(
            {
                "lens": "wearables_sensors",
                "query": "wearable OR biosensor",
                "request_url": "https://api.github.com/search/repositories?q=fixture",
            },
        ),
    )

    assert item.id == "github:101"
    assert item.source == "github"
    assert item.source_item_id == "101"
    assert item.title == "example-health/pulse-lab"
    assert item.description == "A wearable recovery experiment."
    assert item.author == "example-health"
    assert item.published_at == datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc)
    assert item.raw_metrics == {
        "stars": 3,
        "forks": 1,
        "open_issues": 2,
        "language": "Python",
        "topics": ["wearable", "personal-data"],
        "archived": False,
        "created_at": "2026-07-01T09:00:00Z",
        "updated_at": "2026-08-25T11:00:00Z",
        "pushed_at": "2026-08-24T17:30:00Z",
    }
    metadata = item.raw_payload["repository_metadata"]
    assert metadata["license"] == {"spdx_id": "MIT", "name": "MIT License"}
    assert metadata["homepage"] == "https://example.com/pulse-lab"
    assert item.raw_payload["repository"] == payload
    assert item.raw_payload["discovery_lenses"] == ["wearables_sensors"]


def test_numeric_repository_id_survives_rename_without_duplicate(
    tmp_path: Path,
) -> None:
    original_payload = _search_payload()["items"][0]
    renamed_payload = deepcopy(original_payload)
    renamed_payload["name"] = "pulse-studio"
    renamed_payload["full_name"] = "new-owner/pulse-studio"
    renamed_payload["html_url"] = "https://github.com/new-owner/pulse-studio"
    renamed_payload["owner"] = {"login": "new-owner", "id": 10}
    first_item = parse_github_repository(
        original_payload,
        collected_at=TIMESTAMP,
        discovery_contexts=({"lens": "wearables"},),
    )
    second_item = parse_github_repository(
        renamed_payload,
        collected_at=datetime(2026, 8, 28, 15, 0, tzinfo=timezone.utc),
        discovery_contexts=({"lens": "wearables"},),
    )
    storage = SQLiteStorage(tmp_path / "radar.sqlite3")
    storage.initialize()

    assert storage.save_raw_item(first_item) is True
    assert storage.save_raw_item(second_item) is False
    assert storage.count_raw_items() == 1
    stored = storage.get_raw_item_by_source("github", "101")
    assert stored is not None
    assert stored.id == "github:101"
    assert stored.title == "new-owner/pulse-studio"
    assert stored.first_seen_at == TIMESTAMP


def test_collector_uses_configurable_lenses_limits_and_no_default_star_floor() -> None:
    calls: list[tuple[str, dict[str, str]]] = []

    def get_json(url: str, headers: dict[str, str]) -> HttpJsonResponse:
        calls.append((url, dict(headers)))
        return HttpJsonResponse(
            _search_payload(),
            {
                "X-RateLimit-Resource": "search",
                "X-RateLimit-Limit": "10",
                "X-RateLimit-Remaining": "9",
                "X-RateLimit-Used": "1",
                "X-RateLimit-Reset": "1787846400",
            },
        )

    collector = GitHubCollector(
        (_lens("wearables"), _lens("personal_data")),
        limit_per_lens=2,
        recency_days=30,
        readme_limit=0,
        get_json=get_json,
    )

    batch = collector.collect(TIMESTAMP)

    assert not batch.failures
    assert [item.source_item_id for item in batch.items] == ["101", "202"]
    assert [item.raw_metrics["stars"] for item in batch.items] == [3, 1500]
    assert len(calls) == 2
    for url, headers in calls:
        query = parse_qs(urlparse(url).query)
        assert query["sort"] == ["updated"]
        assert query["order"] == ["desc"]
        assert query["per_page"] == ["2"]
        assert "pushed:>=2026-07-28" in query["q"][0]
        assert "stars:>=" not in query["q"][0]
        assert "Authorization" not in headers
        assert headers["Accept"] == "application/vnd.github+json"
        assert headers["X-GitHub-Api-Version"] == API_VERSION
    assert len(collector.rate_limits) == 2
    assert collector.rate_limits[-1].remaining == "9"
    assert batch.items[0].raw_payload["discovery_lenses"] == [
        "wearables",
        "personal_data",
    ]


def test_optional_token_and_low_star_floor_are_sent_only_when_configured() -> None:
    calls: list[tuple[str, dict[str, str]]] = []

    def get_json(url: str, headers: dict[str, str]) -> dict:
        calls.append((url, dict(headers)))
        return _search_payload()

    collector = GitHubCollector(
        (_lens(),),
        limit_per_lens=1,
        recency_days=7,
        min_stars=2,
        token="fixture-token",
        get_json=get_json,
    )

    batch = collector.collect(TIMESTAMP)

    assert len(batch.items) == 1
    query = parse_qs(urlparse(calls[0][0]).query)["q"][0]
    assert "stars:>=2" in query
    assert calls[0][1]["Authorization"] == "Bearer fixture-token"


def test_bounded_readme_excerpt_preserves_its_origin() -> None:
    calls: list[str] = []

    def get_json(url: str, headers: dict[str, str]) -> dict:
        calls.append(url)
        if url.endswith("/readme"):
            return _readme_payload()
        return _search_payload()

    collector = GitHubCollector(
        (_lens(),),
        limit_per_lens=2,
        recency_days=30,
        readme_limit=1,
        get_json=get_json,
    )

    batch = collector.collect(TIMESTAMP)

    assert len(calls) == 2
    assert not batch.failures
    readme = batch.items[0].raw_payload["readme"]
    assert readme["source_url"].endswith("/example-health/pulse-lab/readme")
    assert readme["path"] == "README.md"
    assert "wearable experiment" in readme["excerpt"]
    assert readme["truncated"] is False
    assert "readme" not in batch.items[1].raw_payload


def test_github_collector_enters_the_existing_pipeline(tmp_path: Path) -> None:
    collector = GitHubCollector(
        (_lens(),),
        limit_per_lens=2,
        recency_days=30,
        readme_limit=0,
        get_json=lambda url, headers: _search_payload(),
    )
    storage = SQLiteStorage(tmp_path / "radar.sqlite3")

    result = run_discovery(
        storage,
        (collector,),
        clock=lambda: TIMESTAMP,
        run_id="github-pipeline",
    )

    assert result.run_record.status == "completed"
    assert result.total == 2
    assert result.new_count == 2
    assert result.source_stats[0].source == "github"
    assert storage.count_raw_items() == 2
