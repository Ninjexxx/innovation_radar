"""Repository discovery through the official GitHub REST API."""

from __future__ import annotations

import base64
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.error import HTTPError
from urllib.parse import quote, urlencode

from innovation_radar.collectors.base import CollectionBatch, CollectionFailure
from innovation_radar.collectors.http import HttpClient, HttpJsonResponse
from innovation_radar.config import GitHubLens
from innovation_radar.models import RawItem


API_BASE_URL = "https://api.github.com"
API_VERSION = "2022-11-28"
README_EXCERPT_LENGTH = 1_200
JsonFetcher = Callable[[str, Mapping[str, str]], Any]


@dataclass(frozen=True, slots=True)
class RateLimitSnapshot:
    """Rate-limit metadata exposed by one GitHub response."""

    endpoint: str
    resource: str | None
    limit: str | None
    remaining: str | None
    used: str | None
    reset: str | None

    def as_payload(self) -> dict[str, str | None]:
        return {
            "resource": self.resource,
            "limit": self.limit,
            "remaining": self.remaining,
            "used": self.used,
            "reset": self.reset,
        }


class GitHubCollector:
    """Collect recent or recently active repositories through conceptual lenses."""

    name = "github"

    def __init__(
        self,
        lenses: tuple[GitHubLens, ...],
        limit_per_lens: int,
        recency_days: int,
        *,
        min_stars: int = 0,
        readme_limit: int = 0,
        token: str | None = None,
        get_json: JsonFetcher | None = None,
    ) -> None:
        if not lenses:
            raise ValueError("at least one GitHub lens is required")
        if not 1 <= limit_per_lens <= 100:
            raise ValueError("limit_per_lens must be between 1 and 100")
        if recency_days < 1:
            raise ValueError("recency_days must be positive")
        if min_stars < 0:
            raise ValueError("min_stars must not be negative")
        if readme_limit < 0:
            raise ValueError("readme_limit must not be negative")

        self.lenses = lenses
        self.limit_per_lens = limit_per_lens
        self.recency_days = recency_days
        self.min_stars = min_stars
        self.readme_limit = readme_limit
        self._token = token
        self._get_json = get_json or HttpClient().get_json_response
        self._rate_limits: list[RateLimitSnapshot] = []

    @property
    def rate_limits(self) -> tuple[RateLimitSnapshot, ...]:
        """Return rate-limit observations from the most recent collection."""

        return tuple(self._rate_limits)

    def collect(self, collected_at: datetime) -> CollectionBatch:
        if collected_at.tzinfo is None or collected_at.utcoffset() is None:
            raise ValueError("collected_at must be timezone-aware")

        self._rate_limits = []
        cutoff = (
            collected_at.astimezone(timezone.utc) - timedelta(days=self.recency_days)
        ).date()
        repositories: dict[int, Mapping[str, Any]] = {}
        repository_contexts: dict[int, list[dict[str, Any]]] = {}
        lens_repositories: dict[str, deque[int]] = {
            lens.id: deque() for lens in self.lenses
        }
        failures: list[CollectionFailure] = []

        for lens in self.lenses:
            request_url = build_search_url(
                lens,
                cutoff=cutoff.isoformat(),
                limit=self.limit_per_lens,
                min_stars=self.min_stars,
            )
            try:
                payload, headers = self._request_json(request_url)
                rate_limit = self._capture_rate_limit(request_url, headers)
                if not isinstance(payload, Mapping):
                    raise ValueError("search response must be a JSON object")
                raw_items = payload.get("items")
                if not isinstance(raw_items, list):
                    raise ValueError("search response items must be a JSON array")
                if payload.get("incomplete_results") is True:
                    failures.append(
                        CollectionFailure(
                            self.name,
                            f"lens:{lens.id}",
                            "GitHub search returned incomplete_results=true",
                        )
                    )
            except Exception as error:
                failures.append(
                    CollectionFailure(self.name, f"lens:{lens.id}", str(error))
                )
                continue

            context: dict[str, Any] = {
                "lens": lens.id,
                "description": lens.description,
                "query": lens.query,
                "request_url": request_url,
            }
            if rate_limit is not None:
                context["rate_limit"] = rate_limit.as_payload()

            seen_in_lens: set[int] = set()
            for index, raw_repository in enumerate(raw_items[: self.limit_per_lens]):
                try:
                    if not isinstance(raw_repository, Mapping):
                        raise ValueError("repository result must be a JSON object")
                    repository_id = _repository_id(raw_repository)
                except Exception as error:
                    failures.append(
                        CollectionFailure(
                            self.name,
                            f"lens:{lens.id}:item:{index}",
                            str(error),
                        )
                    )
                    continue

                if repository_id not in repositories:
                    repositories[repository_id] = raw_repository
                    repository_contexts[repository_id] = []
                repository_contexts[repository_id].append(dict(context))
                if repository_id not in seen_in_lens:
                    lens_repositories[lens.id].append(repository_id)
                    seen_in_lens.add(repository_id)

        ordered_ids = _round_robin_repository_ids(self.lenses, lens_repositories)
        readmes: dict[int, dict[str, Any]] = {}
        for repository_id in ordered_ids[: self.readme_limit]:
            repository = repositories[repository_id]
            try:
                full_name = _required_text(repository, "full_name")
                readme_url = _readme_url(full_name)
                readme_payload, headers = self._request_json(readme_url)
                self._capture_rate_limit(readme_url, headers)
                readme = _readme_context(readme_payload, readme_url)
                if readme is not None:
                    readmes[repository_id] = readme
            except HTTPError as error:
                if error.code != 404:
                    failures.append(
                        CollectionFailure(
                            self.name, f"readme:{repository_id}", str(error)
                        )
                    )
            except Exception as error:
                failures.append(
                    CollectionFailure(
                        self.name, f"readme:{repository_id}", str(error)
                    )
                )

        items: list[RawItem] = []
        for repository_id in ordered_ids:
            try:
                items.append(
                    parse_github_repository(
                        repositories[repository_id],
                        collected_at=collected_at,
                        discovery_contexts=tuple(repository_contexts[repository_id]),
                        readme=readmes.get(repository_id),
                    )
                )
            except Exception as error:
                failures.append(
                    CollectionFailure(
                        self.name, f"repository:{repository_id}", str(error)
                    )
                )

        return CollectionBatch(tuple(items), tuple(failures))

    def _request_json(
        self, url: str
    ) -> tuple[Any, Mapping[str, str]]:
        response = self._get_json(url, self._request_headers())
        if isinstance(response, HttpJsonResponse):
            return response.data, response.headers
        return response, {}

    def _request_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": API_VERSION,
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def _capture_rate_limit(
        self, endpoint: str, headers: Mapping[str, str]
    ) -> RateLimitSnapshot | None:
        normalized = {str(key).lower(): str(value) for key, value in headers.items()}
        if not any(key.startswith("x-ratelimit-") for key in normalized):
            return None
        snapshot = RateLimitSnapshot(
            endpoint=endpoint,
            resource=normalized.get("x-ratelimit-resource"),
            limit=normalized.get("x-ratelimit-limit"),
            remaining=normalized.get("x-ratelimit-remaining"),
            used=normalized.get("x-ratelimit-used"),
            reset=normalized.get("x-ratelimit-reset"),
        )
        self._rate_limits.append(snapshot)
        return snapshot


def build_search_url(
    lens: GitHubLens, *, cutoff: str, limit: int, min_stars: int
) -> str:
    """Build a bounded search ordered by activity, never by popularity."""

    query_parts = [lens.query, f"pushed:>={cutoff}"]
    if min_stars > 0:
        query_parts.append(f"stars:>={min_stars}")
    parameters = urlencode(
        {
            "q": " ".join(query_parts),
            "sort": "updated",
            "order": "desc",
            "per_page": str(limit),
            "page": "1",
        }
    )
    return f"{API_BASE_URL}/search/repositories?{parameters}"


def parse_github_repository(
    payload: Mapping[str, Any],
    *,
    collected_at: datetime,
    discovery_contexts: tuple[Mapping[str, Any], ...],
    readme: Mapping[str, Any] | None = None,
) -> RawItem:
    """Normalize a repository without classifying its opportunity relevance."""

    repository_id = _repository_id(payload)
    name = _required_text(payload, "name")
    full_name = _required_text(payload, "full_name")
    url = _required_text(payload, "html_url")
    owner_payload = payload.get("owner")
    if not isinstance(owner_payload, Mapping):
        raise ValueError("repository owner is missing or invalid")
    owner = _required_text(owner_payload, "login")

    created_at = _github_datetime(payload.get("created_at"), "created_at", required=True)
    updated_at = _github_datetime(payload.get("updated_at"), "updated_at")
    pushed_at = _github_datetime(payload.get("pushed_at"), "pushed_at")
    language = _optional_text(payload.get("language"))
    topics = _topics(payload.get("topics"))
    archived = payload.get("archived", False)
    if not isinstance(archived, bool):
        raise ValueError("repository archived must be a boolean")
    homepage = _optional_text(payload.get("homepage"))
    license_metadata = _license_metadata(payload.get("license"))
    description = _optional_text(payload.get("description"))

    stars = _nonnegative_integer(payload, "stargazers_count")
    forks = _nonnegative_integer(payload, "forks_count")
    open_issues = _nonnegative_integer(payload, "open_issues_count")
    source_item_id = str(repository_id)
    lens_ids = tuple(
        context.get("lens")
        for context in discovery_contexts
        if isinstance(context.get("lens"), str)
    )

    normalized_metadata = {
        "name": name,
        "full_name": full_name,
        "owner": owner,
        "created_at": _format_datetime(created_at),
        "updated_at": _format_datetime(updated_at),
        "pushed_at": _format_datetime(pushed_at),
        "language": language,
        "topics": list(topics),
        "stars": stars,
        "forks": forks,
        "open_issues": open_issues,
        "archived": archived,
        "license": license_metadata,
        "homepage": homepage,
    }
    raw_payload: dict[str, Any] = {
        "repository": dict(payload),
        "repository_metadata": normalized_metadata,
        "discovery_lenses": list(dict.fromkeys(lens_ids)),
        "discovery_contexts": [dict(context) for context in discovery_contexts],
    }
    if readme is not None:
        raw_payload["readme"] = dict(readme)

    return RawItem(
        id=f"github:{source_item_id}",
        source="github",
        source_item_id=source_item_id,
        title=full_name,
        description=description,
        url=url,
        author=owner,
        published_at=created_at,
        first_seen_at=collected_at,
        collected_at=collected_at,
        raw_metrics={
            "stars": stars,
            "forks": forks,
            "open_issues": open_issues,
            "language": language,
            "topics": list(topics),
            "archived": archived,
            "created_at": _format_datetime(created_at),
            "updated_at": _format_datetime(updated_at),
            "pushed_at": _format_datetime(pushed_at),
        },
        raw_payload=raw_payload,
    )


def _round_robin_repository_ids(
    lenses: tuple[GitHubLens, ...], lens_repositories: Mapping[str, deque[int]]
) -> list[int]:
    ordered: list[int] = []
    seen: set[int] = set()
    queues = {lens_id: deque(values) for lens_id, values in lens_repositories.items()}
    while True:
        added = False
        for lens in lenses:
            queue = queues[lens.id]
            while queue and queue[0] in seen:
                queue.popleft()
            if not queue:
                continue
            repository_id = queue.popleft()
            seen.add(repository_id)
            ordered.append(repository_id)
            added = True
        if not added:
            return ordered


def _readme_url(full_name: str) -> str:
    try:
        owner, repository = full_name.split("/", 1)
    except ValueError as error:
        raise ValueError("repository full_name must contain owner/name") from error
    return f"{API_BASE_URL}/repos/{quote(owner, safe='')}/{quote(repository, safe='')}/readme"


def _readme_context(payload: Any, source_url: str) -> dict[str, Any] | None:
    if payload is None:
        return None
    if not isinstance(payload, Mapping):
        raise ValueError("README response must be a JSON object")
    content = payload.get("content")
    encoding = payload.get("encoding")
    if not isinstance(content, str) or encoding != "base64":
        return None
    try:
        decoded = base64.b64decode(content).decode("utf-8", errors="replace")
    except (ValueError, TypeError) as error:
        raise ValueError("README content is not valid base64") from error
    excerpt = decoded.strip()[:README_EXCERPT_LENGTH].strip()
    if not excerpt:
        return None
    return {
        "source_url": source_url,
        "html_url": _optional_text(payload.get("html_url")),
        "download_url": _optional_text(payload.get("download_url")),
        "path": _optional_text(payload.get("path")),
        "sha": _optional_text(payload.get("sha")),
        "size": payload.get("size") if isinstance(payload.get("size"), int) else None,
        "excerpt": excerpt,
        "truncated": len(decoded.strip()) > README_EXCERPT_LENGTH,
    }


def _repository_id(payload: Mapping[str, Any]) -> int:
    value = payload.get("id")
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError("repository id is missing or invalid")
    return value


def _required_text(payload: Mapping[str, Any], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"repository {field_name} is missing or invalid")
    return value.strip()


def _optional_text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _nonnegative_integer(payload: Mapping[str, Any], field_name: str) -> int:
    value = payload.get(field_name, 0)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"repository {field_name} must be a non-negative integer")
    return value


def _topics(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or any(not isinstance(topic, str) for topic in value):
        raise ValueError("repository topics must be a JSON array of strings")
    return tuple(topic.strip() for topic in value if topic.strip())


def _license_metadata(value: Any) -> dict[str, str | None] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError("repository license must be a JSON object or null")
    return {
        "spdx_id": _optional_text(value.get("spdx_id")),
        "name": _optional_text(value.get("name")),
    }


def _github_datetime(
    value: Any, field_name: str, *, required: bool = False
) -> datetime | None:
    if value is None and not required:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"repository {field_name} is missing or invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"repository {field_name} is not a valid datetime") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"repository {field_name} must include a timezone")
    return parsed.astimezone(timezone.utc)


def _format_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")
