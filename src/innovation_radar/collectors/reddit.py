"""Behavior and unmet-need discovery through Reddit's approved Data API."""

from __future__ import annotations

import base64
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.error import HTTPError
from urllib.parse import quote, urlencode, urljoin

from innovation_radar.collectors.base import CollectionBatch, CollectionFailure
from innovation_radar.collectors.http import HttpClient, HttpJsonResponse
from innovation_radar.config import RedditLens
from innovation_radar.models import RawItem


TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
API_BASE_URL = "https://oauth.reddit.com"
WEB_BASE_URL = "https://www.reddit.com"
BODY_EXCERPT_LENGTH = 2_000
JsonRequester = Callable[[str, Mapping[str, str]], Any]
TokenProvider = Callable[[], str]


@dataclass(frozen=True, slots=True)
class RedditRateLimitSnapshot:
    """Non-sensitive rate-limit metadata returned by Reddit."""

    endpoint: str
    used: str | None
    remaining: str | None
    reset: str | None


@dataclass(frozen=True, slots=True)
class RedditCollectionStats:
    """Descriptive collection diagnostics without a quality judgment."""

    requests: int = 0
    observed_candidates: int = 0
    unique_candidates: int = 0
    duplicates_avoided: int = 0
    outside_time_window: int = 0
    selected_items: int = 0


class RedditCollector:
    """Collect recent posts through behavioral lenses, never by popularity rank."""

    name = "reddit"

    def __init__(
        self,
        lenses: tuple[RedditLens, ...],
        limit_per_lens: int,
        recency_days: int,
        *,
        new_limit_per_subreddit: int = 0,
        client_id: str | None = None,
        client_secret: str | None = None,
        user_agent: str | None = None,
        token_provider: TokenProvider | None = None,
        get_json: JsonRequester | None = None,
        http_client: HttpClient | None = None,
    ) -> None:
        if not lenses:
            raise ValueError("at least one Reddit lens is required")
        if not 1 <= limit_per_lens <= 100:
            raise ValueError("limit_per_lens must be between 1 and 100")
        if recency_days < 1:
            raise ValueError("recency_days must be positive")
        if not 0 <= new_limit_per_subreddit <= 100:
            raise ValueError("new_limit_per_subreddit must be between 0 and 100")

        self.lenses = lenses
        self.limit_per_lens = limit_per_lens
        self.recency_days = recency_days
        self.new_limit_per_subreddit = new_limit_per_subreddit
        self._client_id = client_id
        self._client_secret = client_secret
        self._user_agent = user_agent
        self._http_client = http_client or HttpClient()
        self._custom_token_provider = token_provider is not None
        self._token_provider = token_provider or self._request_access_token
        self._get_json = get_json or self._http_client.get_json_response
        self._rate_limits: list[RedditRateLimitSnapshot] = []
        self._stats = RedditCollectionStats()
        self._request_count = 0

    @property
    def rate_limits(self) -> tuple[RedditRateLimitSnapshot, ...]:
        return tuple(self._rate_limits)

    @property
    def collection_stats(self) -> RedditCollectionStats:
        return self._stats

    def collect(self, collected_at: datetime) -> CollectionBatch:
        if collected_at.tzinfo is None or collected_at.utcoffset() is None:
            raise ValueError("collected_at must be timezone-aware")

        self._rate_limits = []
        self._request_count = 0
        self._stats = RedditCollectionStats()
        access_problem = self._access_configuration_problem()
        if access_problem is not None:
            return CollectionBatch(
                failures=(CollectionFailure(self.name, "authentication", access_problem),)
            )
        try:
            access_token = self._token_provider()
            if not isinstance(access_token, str) or not access_token.strip():
                raise ValueError("Reddit OAuth returned an empty access token")
        except Exception as error:
            return CollectionBatch(
                failures=(
                    CollectionFailure(
                        self.name,
                        "authentication",
                        f"approved Reddit OAuth access failed: {error}",
                    ),
                )
            )

        cutoff = collected_at.astimezone(timezone.utc) - timedelta(
            days=self.recency_days
        )
        posts: dict[str, Mapping[str, Any]] = {}
        contexts: dict[str, list[dict[str, Any]]] = {}
        group_posts: dict[tuple[str, str], deque[str]] = {
            (lens.id, subreddit.casefold()): deque()
            for lens in self.lenses
            for subreddit in lens.subreddits
        }
        group_seen: dict[tuple[str, str], set[str]] = {
            key: set() for key in group_posts
        }
        failures: list[CollectionFailure] = []
        observed_candidates = 0
        outside_time_window = 0

        def remember(
            payload: Mapping[str, Any],
            context: dict[str, Any],
            group_key: tuple[str, str],
        ) -> None:
            nonlocal observed_candidates, outside_time_window
            post_id = _post_id(payload)
            published_at = _reddit_datetime(payload.get("created_utc"))
            if published_at < cutoff:
                outside_time_window += 1
                return
            observed_candidates += 1
            posts.setdefault(post_id, payload)
            post_contexts = contexts.setdefault(post_id, [])
            if context not in post_contexts:
                post_contexts.append(context)
            if post_id not in group_seen[group_key]:
                group_posts[group_key].append(post_id)
                group_seen[group_key].add(post_id)

        for lens in self.lenses:
            for subreddit in lens.subreddits:
                request_url = build_search_url(
                    lens,
                    subreddit,
                    limit=self.limit_per_lens,
                    recency_days=self.recency_days,
                )
                try:
                    payload, headers = self._request_json(request_url, access_token)
                    rate_limit = self._capture_rate_limit(request_url, headers)
                    raw_posts = _listing_posts(payload)
                except HTTPError as error:
                    failure = self._http_failure(error, f"search:{lens.id}:{subreddit}")
                    failures.append(failure)
                    if error.code in {401, 403, 429}:
                        return self._failed_batch(
                            failures,
                            observed_candidates,
                            posts,
                            outside_time_window,
                        )
                    continue
                except Exception as error:
                    failures.append(
                        CollectionFailure(
                            self.name,
                            f"search:{lens.id}:{subreddit}",
                            str(error),
                        )
                    )
                    continue

                context: dict[str, Any] = {
                    "surface": "search_new",
                    "lens": lens.id,
                    "lens_description": lens.description,
                    "subreddit": subreddit,
                    "query": " OR ".join(lens.queries),
                    "request_url": request_url,
                }
                if rate_limit is not None:
                    context["rate_limit"] = _rate_limit_payload(rate_limit)
                group_key = (lens.id, subreddit.casefold())
                for index, raw_post in enumerate(raw_posts):
                    try:
                        remember(raw_post, context, group_key)
                    except Exception as error:
                        failures.append(
                            CollectionFailure(
                                self.name,
                                f"search:{lens.id}:{subreddit}:item:{index}",
                                str(error),
                            )
                        )

        if self.new_limit_per_subreddit:
            for subreddit, associated_lenses in _community_lenses(self.lenses):
                request_url = build_new_url(
                    subreddit, limit=self.new_limit_per_subreddit
                )
                try:
                    payload, headers = self._request_json(request_url, access_token)
                    rate_limit = self._capture_rate_limit(request_url, headers)
                    raw_posts = _listing_posts(payload)
                except HTTPError as error:
                    failure = self._http_failure(error, f"new:{subreddit}")
                    failures.append(failure)
                    if error.code in {401, 403, 429}:
                        return self._failed_batch(
                            failures,
                            observed_candidates,
                            posts,
                            outside_time_window,
                        )
                    continue
                except Exception as error:
                    failures.append(
                        CollectionFailure(self.name, f"new:{subreddit}", str(error))
                    )
                    continue

                for lens in associated_lenses:
                    context = {
                        "surface": "new",
                        "lens": lens.id,
                        "lens_description": lens.description,
                        "subreddit": subreddit,
                        "query": None,
                        "request_url": request_url,
                    }
                    if rate_limit is not None:
                        context["rate_limit"] = _rate_limit_payload(rate_limit)
                    group_key = (lens.id, subreddit.casefold())
                    for index, raw_post in enumerate(raw_posts):
                        try:
                            remember(raw_post, context, group_key)
                        except Exception as error:
                            failures.append(
                                CollectionFailure(
                                    self.name,
                                    f"new:{subreddit}:item:{index}",
                                    str(error),
                                )
                            )

        ordered_ids = _diverse_post_ids(
            self.lenses, group_posts, self.limit_per_lens
        )
        items: list[RawItem] = []
        for post_id in ordered_ids:
            try:
                items.append(
                    parse_reddit_post(
                        posts[post_id],
                        collected_at=collected_at,
                        discovery_contexts=tuple(contexts[post_id]),
                    )
                )
            except Exception as error:
                failures.append(
                    CollectionFailure(self.name, f"post:{post_id}", str(error))
                )

        self._stats = RedditCollectionStats(
            requests=self._request_count,
            observed_candidates=observed_candidates,
            unique_candidates=len(posts),
            duplicates_avoided=max(0, observed_candidates - len(posts)),
            outside_time_window=outside_time_window,
            selected_items=len(items),
        )
        return CollectionBatch(tuple(items), tuple(failures))

    def _access_configuration_problem(self) -> str | None:
        if not self._user_agent:
            return (
                "Reddit Data API requires an approved OAuth client and a descriptive "
                "User-Agent; configure REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET and "
                "INNOVATION_RADAR_REDDIT_USER_AGENT after Reddit approval"
            )
        if not self._custom_token_provider and (
            not self._client_id or not self._client_secret
        ):
            return (
                "Reddit Data API requires an approved OAuth client; configure "
                "REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET after Reddit approval"
            )
        return None

    def _request_access_token(self) -> str:
        if not self._client_id or not self._client_secret or not self._user_agent:
            raise ValueError("approved Reddit OAuth credentials are not configured")
        credentials = base64.b64encode(
            f"{self._client_id}:{self._client_secret}".encode("utf-8")
        ).decode("ascii")
        response = self._http_client.post_form_json_response(
            TOKEN_URL,
            {"grant_type": "client_credentials"},
            {
                "Authorization": f"Basic {credentials}",
                "User-Agent": self._user_agent,
            },
        )
        payload = response.data
        if not isinstance(payload, Mapping):
            raise ValueError("Reddit OAuth response must be a JSON object")
        token = payload.get("access_token")
        token_type = payload.get("token_type")
        if not isinstance(token, str) or not token.strip():
            raise ValueError("Reddit OAuth response is missing access_token")
        if not isinstance(token_type, str) or token_type.casefold() != "bearer":
            raise ValueError("Reddit OAuth response token_type must be bearer")
        return token.strip()

    def _request_json(
        self, url: str, access_token: str
    ) -> tuple[Any, Mapping[str, str]]:
        self._request_count += 1
        response = self._get_json(
            url,
            {
                "Accept": "application/json",
                "Authorization": f"Bearer {access_token}",
                "User-Agent": str(self._user_agent),
            },
        )
        if isinstance(response, HttpJsonResponse):
            return response.data, response.headers
        return response, {}

    def _capture_rate_limit(
        self, endpoint: str, headers: Mapping[str, str]
    ) -> RedditRateLimitSnapshot | None:
        normalized = {str(key).lower(): str(value) for key, value in headers.items()}
        if not any(key.startswith("x-ratelimit-") for key in normalized):
            return None
        snapshot = RedditRateLimitSnapshot(
            endpoint=endpoint,
            used=normalized.get("x-ratelimit-used"),
            remaining=normalized.get("x-ratelimit-remaining"),
            reset=normalized.get("x-ratelimit-reset"),
        )
        self._rate_limits.append(snapshot)
        return snapshot

    def _http_failure(self, error: HTTPError, context: str) -> CollectionFailure:
        if error.code in {401, 403}:
            message = (
                f"Reddit API access denied with HTTP {error.code}; confirm that the "
                "OAuth client and this business use case have Reddit approval"
            )
        elif error.code == 429:
            message = "Reddit API rate limit reached with HTTP 429; no retry attempted"
        else:
            message = str(error)
        return CollectionFailure(self.name, context, message)

    def _failed_batch(
        self,
        failures: list[CollectionFailure],
        observed_candidates: int,
        posts: Mapping[str, Mapping[str, Any]],
        outside_time_window: int,
    ) -> CollectionBatch:
        self._stats = RedditCollectionStats(
            requests=self._request_count,
            observed_candidates=observed_candidates,
            unique_candidates=len(posts),
            duplicates_avoided=max(0, observed_candidates - len(posts)),
            outside_time_window=outside_time_window,
            selected_items=0,
        )
        return CollectionBatch(failures=tuple(failures))


def build_search_url(
    lens: RedditLens,
    subreddit: str,
    *,
    limit: int,
    recency_days: int,
) -> str:
    """Build a recent search request without popularity ordering."""

    parameters = urlencode(
        {
            "q": " OR ".join(lens.queries),
            "restrict_sr": "true",
            "sort": "new",
            "t": _time_filter(recency_days),
            "limit": str(limit),
            "raw_json": "1",
        }
    )
    return f"{API_BASE_URL}/r/{quote(subreddit, safe='')}/search?{parameters}"


def build_new_url(subreddit: str, *, limit: int) -> str:
    parameters = urlencode({"limit": str(limit), "raw_json": "1"})
    return f"{API_BASE_URL}/r/{quote(subreddit, safe='')}/new?{parameters}"


def parse_reddit_post(
    payload: Mapping[str, Any],
    *,
    collected_at: datetime,
    discovery_contexts: tuple[Mapping[str, Any], ...],
) -> RawItem:
    """Normalize only the public post fields needed for human discovery review."""

    post_id = _post_id(payload)
    title = _required_text(payload, "title")
    subreddit = _required_text(payload, "subreddit")
    permalink = _required_text(payload, "permalink")
    published_at = _reddit_datetime(payload.get("created_utc"))
    score = _integer(payload, "score")
    comments = _integer(payload, "num_comments", minimum=0)
    author = _public_author(payload.get("author"))
    flair = _optional_text(payload.get("link_flair_text"))
    body = _public_body(payload.get("selftext"))
    body_excerpt = body[:BODY_EXCERPT_LENGTH].strip() if body else None
    body_truncated = bool(body and len(body) > BODY_EXCERPT_LENGTH)
    url = urljoin(WEB_BASE_URL, permalink)
    lens_ids = tuple(
        context.get("lens")
        for context in discovery_contexts
        if isinstance(context.get("lens"), str)
    )
    discovered_subreddits = tuple(
        context.get("subreddit")
        for context in discovery_contexts
        if isinstance(context.get("subreddit"), str)
    )

    sanitized_post = {
        "id": post_id,
        "name": _optional_text(payload.get("name")),
        "title": title,
        "selftext_excerpt": body_excerpt,
        "body_truncated": body_truncated,
        "permalink": permalink,
        "external_url": _optional_text(payload.get("url")),
        "author": author,
        "subreddit": subreddit,
        "created_utc": payload.get("created_utc"),
        "score": score,
        "num_comments": comments,
        "link_flair_text": flair,
        "is_self": payload.get("is_self") if isinstance(payload.get("is_self"), bool) else None,
        "over_18": payload.get("over_18") if isinstance(payload.get("over_18"), bool) else None,
        "spoiler": payload.get("spoiler") if isinstance(payload.get("spoiler"), bool) else None,
        "stickied": payload.get("stickied") if isinstance(payload.get("stickied"), bool) else None,
        "locked": payload.get("locked") if isinstance(payload.get("locked"), bool) else None,
    }
    raw_payload = {
        "post": sanitized_post,
        "discovery_lenses": list(dict.fromkeys(lens_ids)),
        "subreddits": list(dict.fromkeys(discovered_subreddits)) or [subreddit],
        "discovery_contexts": [dict(context) for context in discovery_contexts],
        "privacy": {
            "profile_enriched": False,
            "comments_collected": False,
            "body_excerpt_limit": BODY_EXCERPT_LENGTH,
        },
    }
    return RawItem(
        id=f"reddit:{post_id}",
        source="reddit",
        source_item_id=post_id,
        title=title,
        description=body_excerpt,
        url=url,
        author=author,
        published_at=published_at,
        first_seen_at=collected_at,
        collected_at=collected_at,
        raw_metrics={
            "score": score,
            "comments": comments,
            "subreddit": subreddit,
            "flair": flair,
        },
        raw_payload=raw_payload,
    )


def _listing_posts(payload: Any) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(payload, Mapping):
        raise ValueError("Reddit listing response must be a JSON object")
    data = payload.get("data")
    if not isinstance(data, Mapping) or not isinstance(data.get("children"), list):
        raise ValueError("Reddit listing response data.children must be a JSON array")
    posts: list[Mapping[str, Any]] = []
    for child in data["children"]:
        if not isinstance(child, Mapping) or child.get("kind") != "t3":
            raise ValueError("Reddit listing child must be a t3 post")
        post = child.get("data")
        if not isinstance(post, Mapping):
            raise ValueError("Reddit listing post data must be a JSON object")
        posts.append(post)
    return tuple(posts)


def _diverse_post_ids(
    lenses: tuple[RedditLens, ...],
    group_posts: Mapping[tuple[str, str], deque[str]],
    limit_per_lens: int,
) -> list[str]:
    lens_queues: dict[str, deque[str]] = {}
    for lens in lenses:
        community_queues = [
            deque(group_posts[(lens.id, subreddit.casefold())])
            for subreddit in lens.subreddits
        ]
        candidates: list[str] = []
        seen_in_lens: set[str] = set()
        while len(candidates) < limit_per_lens:
            added = False
            for queue in community_queues:
                while queue and queue[0] in seen_in_lens:
                    queue.popleft()
                if not queue:
                    continue
                post_id = queue.popleft()
                seen_in_lens.add(post_id)
                candidates.append(post_id)
                added = True
                if len(candidates) == limit_per_lens:
                    break
            if not added:
                break
        lens_queues[lens.id] = deque(candidates)

    ordered: list[str] = []
    seen: set[str] = set()
    while True:
        added = False
        for lens in lenses:
            queue = lens_queues[lens.id]
            while queue and queue[0] in seen:
                queue.popleft()
            if not queue:
                continue
            post_id = queue.popleft()
            seen.add(post_id)
            ordered.append(post_id)
            added = True
        if not added:
            return ordered


def _community_lenses(
    lenses: tuple[RedditLens, ...],
) -> tuple[tuple[str, tuple[RedditLens, ...]], ...]:
    communities: dict[str, tuple[str, list[RedditLens]]] = {}
    for lens in lenses:
        for subreddit in lens.subreddits:
            key = subreddit.casefold()
            if key not in communities:
                communities[key] = (subreddit, [])
            communities[key][1].append(lens)
    return tuple(
        (subreddit, tuple(associated))
        for subreddit, associated in communities.values()
    )


def _time_filter(recency_days: int) -> str:
    if recency_days <= 1:
        return "day"
    if recency_days <= 7:
        return "week"
    if recency_days <= 31:
        return "month"
    if recency_days <= 365:
        return "year"
    return "all"


def _post_id(payload: Mapping[str, Any]) -> str:
    return _required_text(payload, "id")


def _required_text(payload: Mapping[str, Any], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Reddit post {field_name} is missing or invalid")
    return value.strip()


def _optional_text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _public_author(value: Any) -> str | None:
    author = _optional_text(value)
    if author is None or author.casefold() in {"[deleted]", "[removed]"}:
        return None
    return author


def _public_body(value: Any) -> str | None:
    body = _optional_text(value)
    if body is None or body.casefold() in {"[deleted]", "[removed]"}:
        return None
    return body


def _integer(
    payload: Mapping[str, Any], field_name: str, *, minimum: int | None = None
) -> int:
    value = payload.get(field_name, 0)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"Reddit post {field_name} must be an integer")
    if minimum is not None and value < minimum:
        raise ValueError(f"Reddit post {field_name} must be at least {minimum}")
    return value


def _reddit_datetime(value: Any) -> datetime:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("Reddit post created_utc is missing or invalid")
    try:
        return datetime.fromtimestamp(value, timezone.utc)
    except (OSError, OverflowError, ValueError) as error:
        raise ValueError("Reddit post created_utc is outside the supported range") from error


def _rate_limit_payload(
    snapshot: RedditRateLimitSnapshot,
) -> dict[str, str | None]:
    return {
        "used": snapshot.used,
        "remaining": snapshot.remaining,
        "reset": snapshot.reset,
    }
