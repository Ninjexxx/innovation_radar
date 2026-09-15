"""Environment-based configuration for the innovation radar."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from os import environ as process_environment
from pathlib import Path
from typing import Mapping
from urllib.parse import urlparse


DATABASE_PATH_ENV = "INNOVATION_RADAR_DB_PATH"
LOG_LEVEL_ENV = "INNOVATION_RADAR_LOG_LEVEL"
REPORT_DIRECTORY_ENV = "INNOVATION_RADAR_REPORT_DIR"
HN_LIMIT_ENV = "INNOVATION_RADAR_HN_LIMIT"
RSS_LIMIT_ENV = "INNOVATION_RADAR_RSS_LIMIT"
RSS_FEEDS_ENV = "INNOVATION_RADAR_RSS_FEEDS"
REVIEW_SAMPLE_LIMIT_ENV = "INNOVATION_RADAR_REVIEW_SAMPLE_LIMIT"
GITHUB_LENSES_ENV = "INNOVATION_RADAR_GITHUB_LENSES"
GITHUB_LIMIT_ENV = "INNOVATION_RADAR_GITHUB_LIMIT"
GITHUB_RECENCY_DAYS_ENV = "INNOVATION_RADAR_GITHUB_RECENCY_DAYS"
GITHUB_MIN_STARS_ENV = "INNOVATION_RADAR_GITHUB_MIN_STARS"
GITHUB_README_LIMIT_ENV = "INNOVATION_RADAR_GITHUB_README_LIMIT"
GITHUB_TOKEN_ENV = "GITHUB_TOKEN"
REDDIT_LENSES_ENV = "INNOVATION_RADAR_REDDIT_LENSES"
REDDIT_LIMIT_ENV = "INNOVATION_RADAR_REDDIT_LIMIT"
REDDIT_NEW_LIMIT_ENV = "INNOVATION_RADAR_REDDIT_NEW_LIMIT"
REDDIT_RECENCY_DAYS_ENV = "INNOVATION_RADAR_REDDIT_RECENCY_DAYS"
REDDIT_USER_AGENT_ENV = "INNOVATION_RADAR_REDDIT_USER_AGENT"
REDDIT_CLIENT_ID_ENV = "REDDIT_CLIENT_ID"
REDDIT_CLIENT_SECRET_ENV = "REDDIT_CLIENT_SECRET"
ANALYSIS_PROVIDER_ENV = "INNOVATION_RADAR_ANALYSIS_PROVIDER"
DEFAULT_DATABASE_PATH = Path("data/innovation_radar.sqlite3")
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_REPORT_DIRECTORY = Path("data/reports")
DEFAULT_HN_LIMIT = 2
DEFAULT_RSS_LIMIT = 2
DEFAULT_REVIEW_SAMPLE_LIMIT = 12
DEFAULT_GITHUB_LIMIT = 2
DEFAULT_GITHUB_RECENCY_DAYS = 60
DEFAULT_GITHUB_MIN_STARS = 0
DEFAULT_GITHUB_README_LIMIT = 10
DEFAULT_REDDIT_LIMIT = 8
DEFAULT_REDDIT_NEW_LIMIT = 2
DEFAULT_REDDIT_RECENCY_DAYS = 30
DEFAULT_ANALYSIS_PROVIDER = "heuristic-offline"
VALID_ANALYSIS_PROVIDERS = frozenset({"heuristic-offline"})
VALID_LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})
FEED_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
LENS_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
SUBREDDIT_PATTERN = re.compile(r"^[A-Za-z0-9_]{2,21}$")
BOOLEAN_OPERATOR_PATTERN = re.compile(r"\b(?:AND|OR|NOT)\b", re.IGNORECASE)


class ConfigError(ValueError):
    """Raised when environment configuration is invalid."""


@dataclass(frozen=True, slots=True)
class FeedConfig:
    """Configuration for one generic RSS or Atom feed."""

    id: str
    name: str
    url: str
    category: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.id, str):
            raise ConfigError("RSS feed id must be a string")
        if not isinstance(self.name, str):
            raise ConfigError("RSS feed name must be a string")
        if not isinstance(self.url, str):
            raise ConfigError("RSS feed URL must be a string")
        if self.category is not None and not isinstance(self.category, str):
            raise ConfigError("RSS feed category must be a string when provided")

        feed_id = self.id.strip()
        name = self.name.strip()
        url = self.url.strip()
        category = self.category.strip() if self.category is not None else None

        if not FEED_ID_PATTERN.fullmatch(feed_id):
            raise ConfigError(
                "RSS feed id must use lowercase letters, numbers, hyphens or underscores"
            )
        if not name:
            raise ConfigError("RSS feed name must not be empty")
        parsed_url = urlparse(url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise ConfigError(f"RSS feed URL must be HTTP(S): {self.url!r}")
        if category == "":
            raise ConfigError("RSS feed category must not be empty when provided")

        object.__setattr__(self, "id", feed_id)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "url", url)
        object.__setattr__(self, "category", category)


@dataclass(frozen=True, slots=True)
class GitHubLens:
    """One configurable conceptual lens for repository discovery."""

    id: str
    description: str
    query: str

    def __post_init__(self) -> None:
        for field_name in ("id", "description", "query"):
            if not isinstance(getattr(self, field_name), str):
                raise ConfigError(f"GitHub lens {field_name} must be a string")

        lens_id = self.id.strip()
        description = self.description.strip()
        query = " ".join(self.query.split())
        if not LENS_ID_PATTERN.fullmatch(lens_id):
            raise ConfigError(
                "GitHub lens id must use lowercase letters, numbers, hyphens or underscores"
            )
        if not description:
            raise ConfigError("GitHub lens description must not be empty")
        if not query:
            raise ConfigError("GitHub lens query must not be empty")
        if len(query) > 256:
            raise ConfigError("GitHub lens query must not exceed 256 characters")
        if len(BOOLEAN_OPERATOR_PATTERN.findall(query)) > 5:
            raise ConfigError(
                "GitHub lens query must not contain more than five boolean operators"
            )

        object.__setattr__(self, "id", lens_id)
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "query", query)


@dataclass(frozen=True, slots=True)
class RedditLens:
    """One configurable behavioral lens and its candidate communities."""

    id: str
    description: str
    queries: tuple[str, ...]
    subreddits: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.id, str):
            raise ConfigError("Reddit lens id must be a string")
        if not isinstance(self.description, str):
            raise ConfigError("Reddit lens description must be a string")
        if not isinstance(self.queries, (list, tuple)) or any(
            not isinstance(query, str) for query in self.queries
        ):
            raise ConfigError("Reddit lens queries must be an array of strings")
        if not isinstance(self.subreddits, (list, tuple)) or any(
            not isinstance(subreddit, str) for subreddit in self.subreddits
        ):
            raise ConfigError("Reddit lens subreddits must be an array of strings")

        lens_id = self.id.strip()
        description = self.description.strip()
        queries = tuple(" ".join(query.split()) for query in self.queries)
        subreddits = tuple(subreddit.strip() for subreddit in self.subreddits)
        if not LENS_ID_PATTERN.fullmatch(lens_id):
            raise ConfigError(
                "Reddit lens id must use lowercase letters, numbers, hyphens or underscores"
            )
        if not description:
            raise ConfigError("Reddit lens description must not be empty")
        if not queries or any(not query for query in queries):
            raise ConfigError("Reddit lens must contain at least one non-empty query")
        combined_query = " OR ".join(queries)
        if len(combined_query) > 512:
            raise ConfigError("Reddit lens combined query must not exceed 512 characters")
        if not subreddits:
            raise ConfigError("Reddit lens must contain at least one subreddit")
        invalid_subreddits = [
            subreddit
            for subreddit in subreddits
            if not SUBREDDIT_PATTERN.fullmatch(subreddit)
        ]
        if invalid_subreddits:
            raise ConfigError(
                "Reddit subreddit names must omit r/ and use 2-21 letters, numbers or underscores"
            )
        normalized_names = [subreddit.casefold() for subreddit in subreddits]
        if len(normalized_names) != len(set(normalized_names)):
            raise ConfigError("Reddit lens subreddit names must be unique")

        object.__setattr__(self, "id", lens_id)
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "queries", queries)
        object.__setattr__(self, "subreddits", subreddits)


DEFAULT_RSS_FEEDS = (
    FeedConfig(
        id="mit_ai",
        name="MIT News — Artificial Intelligence",
        url="https://news.mit.edu/rss/topic/artificial-intelligence2",
        category="research",
    ),
    FeedConfig(
        id="google_health",
        name="Google — Health",
        url="https://blog.google/technology/health/rss/",
        category="health",
    ),
    FeedConfig(
        id="medium_healthtech",
        name="Medium — Healthtech",
        url="https://medium.com/feed/tag/healthtech",
        category="health",
    ),
)


DEFAULT_GITHUB_LENSES = (
    GitHubLens(
        id="health_wellness",
        description="Health and wellness capabilities or experiments",
        query='"digital health" OR wellness',
    ),
    GitHubLens(
        id="wearables_sensors",
        description="Wearables, biosensors and sensing experiments",
        query='wearable OR biosensor OR "health sensor"',
    ),
    GitHubLens(
        id="voice_vision_multimodal",
        description="Voice, computer vision and multimodal interaction",
        query='voice OR "computer vision" OR multimodal',
    ),
    GitHubLens(
        id="local_new_interfaces",
        description="On-device or local capabilities and new interfaces",
        query='"on-device" OR "local-first" OR "spatial interface"',
    ),
    GitHubLens(
        id="personal_data_experiments",
        description="Personal data, self-tracking and transferable experiments",
        query='"personal data" OR "quantified-self" OR "self-tracking"',
    ),
)


DEFAULT_REDDIT_LENSES = (
    RedditLens(
        id="personal_health_behavior",
        description="Personal attempts to understand or combine health data",
        queries=(
            '"self tracking"',
            '"sleep tracking"',
            "symptoms",
            "wearable",
            "biomarkers",
            '"health dashboard"',
        ),
        subreddits=("QuantifiedSelf", "ouraring", "Garmin"),
    ),
    RedditLens(
        id="unmet_needs",
        description="Needs, workarounds and things people wish existed",
        queries=(
            '"is there anything"',
            '"does anyone know a way"',
            '"why doesn\'t"',
            '"I wish"',
            '"how do you track"',
            '"how do you manage"',
        ),
        subreddits=("QuantifiedSelf", "caregiving", "disability"),
    ),
    RedditLens(
        id="ai_in_real_life",
        description="Concrete or unexpected uses of AI in everyday life",
        queries=(
            '"I built"',
            '"I use AI"',
            '"I made"',
            '"I combined"',
            '"my workflow"',
        ),
        subreddits=("LocalLLaMA", "selfhosted", "ChatGPT"),
    ),
    RedditLens(
        id="accessibility_care_interfaces",
        description="Accessibility, care and simpler interface experiences",
        queries=(
            "accessibility",
            "caregiver",
            '"remote care"',
            "elderly",
            "voice",
            '"ambient computing"',
        ),
        subreddits=("accessibility", "caregiving", "AgingParents"),
    ),
    RedditLens(
        id="personal_data_and_automation",
        description="Personal data, local tools and cross-service automation",
        queries=(
            '"personal data"',
            "automation",
            "dashboard",
            "sensors",
            '"local tools"',
            '"personal workflow"',
        ),
        subreddits=("selfhosted", "homeassistant", "ObsidianMD"),
    ),
)


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime settings loaded directly from environment variables."""

    database_path: Path
    log_level: str
    report_directory: Path
    hn_limit_per_surface: int
    rss_limit_per_feed: int
    rss_feeds: tuple[FeedConfig, ...]
    review_sample_limit: int
    github_lenses: tuple[GitHubLens, ...]
    github_limit_per_lens: int
    github_recency_days: int
    github_min_stars: int
    github_readme_limit: int
    github_token: str | None = field(repr=False)
    reddit_lenses: tuple[RedditLens, ...]
    reddit_limit_per_lens: int
    reddit_new_limit_per_subreddit: int
    reddit_recency_days: int
    reddit_user_agent: str | None
    reddit_client_id: str | None = field(repr=False)
    reddit_client_secret: str | None = field(repr=False)
    analysis_provider: str = DEFAULT_ANALYSIS_PROVIDER

    @classmethod
    def from_env(cls, values: Mapping[str, str] | None = None) -> "Settings":
        environment = process_environment if values is None else values

        raw_database_path = environment.get(DATABASE_PATH_ENV)
        if raw_database_path is None:
            database_path = DEFAULT_DATABASE_PATH
        elif not raw_database_path.strip():
            raise ConfigError(f"{DATABASE_PATH_ENV} must not be empty")
        else:
            database_path = Path(raw_database_path).expanduser()

        raw_report_directory = environment.get(REPORT_DIRECTORY_ENV)
        if raw_report_directory is None:
            report_directory = DEFAULT_REPORT_DIRECTORY
        elif not raw_report_directory.strip():
            raise ConfigError(f"{REPORT_DIRECTORY_ENV} must not be empty")
        else:
            report_directory = Path(raw_report_directory).expanduser()

        raw_log_level = environment.get(LOG_LEVEL_ENV, DEFAULT_LOG_LEVEL)
        log_level = raw_log_level.strip().upper()
        if log_level not in VALID_LOG_LEVELS:
            allowed = ", ".join(sorted(VALID_LOG_LEVELS))
            raise ConfigError(
                f"{LOG_LEVEL_ENV} must be one of: {allowed}; got {raw_log_level!r}"
            )

        hn_limit = _positive_limit(
            environment.get(HN_LIMIT_ENV), HN_LIMIT_ENV, DEFAULT_HN_LIMIT
        )
        rss_limit = _positive_limit(
            environment.get(RSS_LIMIT_ENV), RSS_LIMIT_ENV, DEFAULT_RSS_LIMIT
        )
        review_sample_limit = _positive_limit(
            environment.get(REVIEW_SAMPLE_LIMIT_ENV),
            REVIEW_SAMPLE_LIMIT_ENV,
            DEFAULT_REVIEW_SAMPLE_LIMIT,
        )
        rss_feeds = _rss_feeds(environment.get(RSS_FEEDS_ENV))
        github_lenses = _github_lenses(environment.get(GITHUB_LENSES_ENV))
        github_limit = _integer_in_range(
            environment.get(GITHUB_LIMIT_ENV),
            GITHUB_LIMIT_ENV,
            DEFAULT_GITHUB_LIMIT,
            minimum=1,
            maximum=20,
        )
        github_recency_days = _integer_in_range(
            environment.get(GITHUB_RECENCY_DAYS_ENV),
            GITHUB_RECENCY_DAYS_ENV,
            DEFAULT_GITHUB_RECENCY_DAYS,
            minimum=1,
            maximum=3650,
        )
        github_min_stars = _integer_in_range(
            environment.get(GITHUB_MIN_STARS_ENV),
            GITHUB_MIN_STARS_ENV,
            DEFAULT_GITHUB_MIN_STARS,
            minimum=0,
            maximum=100,
        )
        github_readme_limit = _integer_in_range(
            environment.get(GITHUB_README_LIMIT_ENV),
            GITHUB_README_LIMIT_ENV,
            DEFAULT_GITHUB_README_LIMIT,
            minimum=0,
            maximum=50,
        )
        raw_github_token = environment.get(GITHUB_TOKEN_ENV)
        if raw_github_token is None:
            github_token = None
        elif not raw_github_token.strip():
            raise ConfigError(f"{GITHUB_TOKEN_ENV} must not be empty when provided")
        else:
            github_token = raw_github_token.strip()

        reddit_lenses = _reddit_lenses(environment.get(REDDIT_LENSES_ENV))
        reddit_limit = _integer_in_range(
            environment.get(REDDIT_LIMIT_ENV),
            REDDIT_LIMIT_ENV,
            DEFAULT_REDDIT_LIMIT,
            minimum=1,
            maximum=20,
        )
        reddit_new_limit = _integer_in_range(
            environment.get(REDDIT_NEW_LIMIT_ENV),
            REDDIT_NEW_LIMIT_ENV,
            DEFAULT_REDDIT_NEW_LIMIT,
            minimum=0,
            maximum=10,
        )
        reddit_recency_days = _integer_in_range(
            environment.get(REDDIT_RECENCY_DAYS_ENV),
            REDDIT_RECENCY_DAYS_ENV,
            DEFAULT_REDDIT_RECENCY_DAYS,
            minimum=1,
            maximum=365,
        )
        reddit_client_id = _optional_nonempty(
            environment.get(REDDIT_CLIENT_ID_ENV), REDDIT_CLIENT_ID_ENV
        )
        reddit_client_secret = _optional_nonempty(
            environment.get(REDDIT_CLIENT_SECRET_ENV), REDDIT_CLIENT_SECRET_ENV
        )
        reddit_user_agent = _optional_nonempty(
            environment.get(REDDIT_USER_AGENT_ENV), REDDIT_USER_AGENT_ENV
        )
        reddit_access_values = (
            reddit_client_id,
            reddit_client_secret,
            reddit_user_agent,
        )
        if any(value is not None for value in reddit_access_values) and not all(
            value is not None for value in reddit_access_values
        ):
            raise ConfigError(
                f"{REDDIT_CLIENT_ID_ENV}, {REDDIT_CLIENT_SECRET_ENV} and "
                f"{REDDIT_USER_AGENT_ENV} must be provided together"
            )
        if reddit_user_agent is not None and "(by /u/" not in reddit_user_agent:
            raise ConfigError(
                f"{REDDIT_USER_AGENT_ENV} must identify the app and include '(by /u/<username>)'"
            )

        analysis_provider = _analysis_provider(environment.get(ANALYSIS_PROVIDER_ENV))

        return cls(
            database_path=database_path,
            log_level=log_level,
            report_directory=report_directory,
            hn_limit_per_surface=hn_limit,
            rss_limit_per_feed=rss_limit,
            rss_feeds=rss_feeds,
            review_sample_limit=review_sample_limit,
            github_lenses=github_lenses,
            github_limit_per_lens=github_limit,
            github_recency_days=github_recency_days,
            github_min_stars=github_min_stars,
            github_readme_limit=github_readme_limit,
            github_token=github_token,
            reddit_lenses=reddit_lenses,
            reddit_limit_per_lens=reddit_limit,
            reddit_new_limit_per_subreddit=reddit_new_limit,
            reddit_recency_days=reddit_recency_days,
            reddit_user_agent=reddit_user_agent,
            reddit_client_id=reddit_client_id,
            reddit_client_secret=reddit_client_secret,
            analysis_provider=analysis_provider,
        )


def _positive_limit(raw_value: str | None, name: str, default: int) -> int:
    return _integer_in_range(raw_value, name, default, minimum=1, maximum=100)


def _integer_in_range(
    raw_value: str | None,
    name: str,
    default: int,
    *,
    minimum: int,
    maximum: int,
) -> int:
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except ValueError as error:
        raise ConfigError(f"{name} must be an integer") from error
    if not minimum <= value <= maximum:
        raise ConfigError(f"{name} must be between {minimum} and {maximum}")
    return value


def _analysis_provider(raw_value: str | None) -> str:
    if raw_value is None:
        return DEFAULT_ANALYSIS_PROVIDER
    value = raw_value.strip()
    if value not in VALID_ANALYSIS_PROVIDERS:
        allowed = ", ".join(sorted(VALID_ANALYSIS_PROVIDERS))
        raise ConfigError(
            f"{ANALYSIS_PROVIDER_ENV} must be one of: {allowed}; got {raw_value!r}"
        )
    return value


def _optional_nonempty(raw_value: str | None, name: str) -> str | None:
    if raw_value is None:
        return None
    value = raw_value.strip()
    if not value:
        raise ConfigError(f"{name} must not be empty when provided")
    return value


def _rss_feeds(raw_value: str | None) -> tuple[FeedConfig, ...]:
    if raw_value is None:
        return DEFAULT_RSS_FEEDS
    try:
        entries = json.loads(raw_value)
    except json.JSONDecodeError as error:
        raise ConfigError(f"{RSS_FEEDS_ENV} must be valid JSON") from error
    if not isinstance(entries, list):
        raise ConfigError(f"{RSS_FEEDS_ENV} must be a JSON array")

    feeds: list[FeedConfig] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ConfigError(f"{RSS_FEEDS_ENV}[{index}] must be an object")
        try:
            feed = FeedConfig(**entry)
        except TypeError as error:
            raise ConfigError(f"invalid RSS feed at index {index}: {error}") from error
        feeds.append(feed)

    feed_ids = [feed.id for feed in feeds]
    if len(feed_ids) != len(set(feed_ids)):
        raise ConfigError(f"{RSS_FEEDS_ENV} feed ids must be unique")
    return tuple(feeds)


def _github_lenses(raw_value: str | None) -> tuple[GitHubLens, ...]:
    if raw_value is None:
        return DEFAULT_GITHUB_LENSES
    try:
        entries = json.loads(raw_value)
    except json.JSONDecodeError as error:
        raise ConfigError(f"{GITHUB_LENSES_ENV} must be valid JSON") from error
    if not isinstance(entries, list):
        raise ConfigError(f"{GITHUB_LENSES_ENV} must be a JSON array")
    if not entries:
        raise ConfigError(f"{GITHUB_LENSES_ENV} must contain at least one lens")

    lenses: list[GitHubLens] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ConfigError(f"{GITHUB_LENSES_ENV}[{index}] must be an object")
        try:
            lens = GitHubLens(**entry)
        except TypeError as error:
            raise ConfigError(f"invalid GitHub lens at index {index}: {error}") from error
        lenses.append(lens)

    lens_ids = [lens.id for lens in lenses]
    if len(lens_ids) != len(set(lens_ids)):
        raise ConfigError(f"{GITHUB_LENSES_ENV} lens ids must be unique")
    return tuple(lenses)


def _reddit_lenses(raw_value: str | None) -> tuple[RedditLens, ...]:
    if raw_value is None:
        return DEFAULT_REDDIT_LENSES
    try:
        entries = json.loads(raw_value)
    except json.JSONDecodeError as error:
        raise ConfigError(f"{REDDIT_LENSES_ENV} must be valid JSON") from error
    if not isinstance(entries, list):
        raise ConfigError(f"{REDDIT_LENSES_ENV} must be a JSON array")
    if not entries:
        raise ConfigError(f"{REDDIT_LENSES_ENV} must contain at least one lens")

    lenses: list[RedditLens] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ConfigError(f"{REDDIT_LENSES_ENV}[{index}] must be an object")
        try:
            lens = RedditLens(**entry)
        except TypeError as error:
            raise ConfigError(f"invalid Reddit lens at index {index}: {error}") from error
        lenses.append(lens)

    lens_ids = [lens.id for lens in lenses]
    if len(lens_ids) != len(set(lens_ids)):
        raise ConfigError(f"{REDDIT_LENSES_ENV} lens ids must be unique")
    return tuple(lenses)
