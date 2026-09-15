import json
from pathlib import Path

import pytest

from innovation_radar.config import (
    DATABASE_PATH_ENV,
    DEFAULT_DATABASE_PATH,
    DEFAULT_GITHUB_LENSES,
    DEFAULT_LOG_LEVEL,
    DEFAULT_REDDIT_LENSES,
    GITHUB_LENSES_ENV,
    GITHUB_LIMIT_ENV,
    GITHUB_MIN_STARS_ENV,
    GITHUB_README_LIMIT_ENV,
    GITHUB_RECENCY_DAYS_ENV,
    GITHUB_TOKEN_ENV,
    LOG_LEVEL_ENV,
    REDDIT_CLIENT_ID_ENV,
    REDDIT_CLIENT_SECRET_ENV,
    REDDIT_LENSES_ENV,
    REDDIT_LIMIT_ENV,
    REDDIT_NEW_LIMIT_ENV,
    REDDIT_RECENCY_DAYS_ENV,
    REDDIT_USER_AGENT_ENV,
    REVIEW_SAMPLE_LIMIT_ENV,
    RSS_FEEDS_ENV,
    ConfigError,
    Settings,
)


def test_default_configuration() -> None:
    settings = Settings.from_env({})

    assert settings.database_path == DEFAULT_DATABASE_PATH
    assert settings.log_level == DEFAULT_LOG_LEVEL
    assert settings.github_lenses == DEFAULT_GITHUB_LENSES
    assert settings.github_min_stars == 0
    assert settings.github_token is None
    assert settings.reddit_lenses == DEFAULT_REDDIT_LENSES
    assert settings.reddit_limit_per_lens == 8
    assert settings.reddit_new_limit_per_subreddit == 2
    assert settings.reddit_recency_days == 30
    assert settings.reddit_client_id is None
    assert settings.reddit_client_secret is None


def test_environment_overrides_configuration(tmp_path: Path) -> None:
    database_path = tmp_path / "custom.sqlite3"

    settings = Settings.from_env(
        {
            DATABASE_PATH_ENV: str(database_path),
            LOG_LEVEL_ENV: "debug",
        }
    )

    assert settings.database_path == database_path
    assert settings.log_level == "DEBUG"


def test_rss_feeds_are_loaded_from_json_configuration() -> None:
    feeds = [
        {
            "id": "custom",
            "name": "custom",
            "url": "https://example.com/feed.xml",
            "category": "validation",
        }
    ]

    settings = Settings.from_env({RSS_FEEDS_ENV: json.dumps(feeds)})

    assert len(settings.rss_feeds) == 1
    assert settings.rss_feeds[0].id == "custom"
    assert settings.rss_feeds[0].name == "custom"
    assert settings.rss_feeds[0].category == "validation"


def test_github_discovery_configuration_can_be_overridden() -> None:
    lenses = [
        {
            "id": "transferable",
            "description": "Transferable experiments",
            "query": '"personal data" OR experiment',
        }
    ]

    settings = Settings.from_env(
        {
            GITHUB_LENSES_ENV: json.dumps(lenses),
            GITHUB_LIMIT_ENV: "4",
            GITHUB_RECENCY_DAYS_ENV: "21",
            GITHUB_MIN_STARS_ENV: "2",
            GITHUB_README_LIMIT_ENV: "3",
            GITHUB_TOKEN_ENV: "test-token",
        }
    )

    assert [lens.id for lens in settings.github_lenses] == ["transferable"]
    assert settings.github_lenses[0].query == '"personal data" OR experiment'
    assert settings.github_limit_per_lens == 4
    assert settings.github_recency_days == 21
    assert settings.github_min_stars == 2
    assert settings.github_readme_limit == 3
    assert settings.github_token == "test-token"
    assert "test-token" not in repr(settings)


def test_reddit_lenses_communities_window_and_oauth_can_be_configured() -> None:
    lenses = [
        {
            "id": "needs",
            "description": "Unmet needs and workarounds",
            "queries": ["I wish", "how do you manage"],
            "subreddits": ["QuantifiedSelf", "caregiving"],
        }
    ]
    user_agent = "windows:namu-radar:v0.1 (by /u/approved_user)"

    settings = Settings.from_env(
        {
            REDDIT_LENSES_ENV: json.dumps(lenses),
            REDDIT_LIMIT_ENV: "7",
            REDDIT_NEW_LIMIT_ENV: "3",
            REDDIT_RECENCY_DAYS_ENV: "21",
            REDDIT_CLIENT_ID_ENV: "client-id",
            REDDIT_CLIENT_SECRET_ENV: "client-secret",
            REDDIT_USER_AGENT_ENV: user_agent,
        }
    )

    assert [lens.id for lens in settings.reddit_lenses] == ["needs"]
    assert settings.reddit_lenses[0].queries == ("I wish", "how do you manage")
    assert settings.reddit_lenses[0].subreddits == (
        "QuantifiedSelf",
        "caregiving",
    )
    assert settings.reddit_limit_per_lens == 7
    assert settings.reddit_new_limit_per_subreddit == 3
    assert settings.reddit_recency_days == 21
    assert settings.reddit_user_agent == user_agent
    assert settings.reddit_client_id == "client-id"
    assert settings.reddit_client_secret == "client-secret"
    assert "client-id" not in repr(settings)
    assert "client-secret" not in repr(settings)


@pytest.mark.parametrize(
    ("environment", "expected_message"),
    [
        ({DATABASE_PATH_ENV: "   "}, DATABASE_PATH_ENV),
        ({LOG_LEVEL_ENV: "verbose"}, LOG_LEVEL_ENV),
        ({RSS_FEEDS_ENV: "not-json"}, RSS_FEEDS_ENV),
        (
            {RSS_FEEDS_ENV: '[{"id":"bad","name":"Bad","url":42}]'},
            "RSS feed URL must be a string",
        ),
        ({REVIEW_SAMPLE_LIMIT_ENV: "101"}, REVIEW_SAMPLE_LIMIT_ENV),
        ({GITHUB_LENSES_ENV: "[]"}, GITHUB_LENSES_ENV),
        (
            {
                GITHUB_LENSES_ENV: json.dumps(
                    [
                        {"id": "same", "description": "One", "query": "one"},
                        {"id": "same", "description": "Two", "query": "two"},
                    ]
                )
            },
            "lens ids must be unique",
        ),
        ({GITHUB_LIMIT_ENV: "0"}, GITHUB_LIMIT_ENV),
        ({GITHUB_RECENCY_DAYS_ENV: "0"}, GITHUB_RECENCY_DAYS_ENV),
        ({GITHUB_MIN_STARS_ENV: "101"}, GITHUB_MIN_STARS_ENV),
        ({GITHUB_README_LIMIT_ENV: "51"}, GITHUB_README_LIMIT_ENV),
        ({GITHUB_TOKEN_ENV: "   "}, GITHUB_TOKEN_ENV),
        ({REDDIT_LENSES_ENV: "[]"}, REDDIT_LENSES_ENV),
        (
            {
                REDDIT_LENSES_ENV: json.dumps(
                    [
                        {
                            "id": "needs",
                            "description": "Needs",
                            "queries": ["I wish"],
                            "subreddits": ["r/caregiving"],
                        }
                    ]
                )
            },
            "Reddit subreddit names",
        ),
        ({REDDIT_LIMIT_ENV: "0"}, REDDIT_LIMIT_ENV),
        ({REDDIT_NEW_LIMIT_ENV: "11"}, REDDIT_NEW_LIMIT_ENV),
        ({REDDIT_RECENCY_DAYS_ENV: "0"}, REDDIT_RECENCY_DAYS_ENV),
        ({REDDIT_CLIENT_ID_ENV: "client-only"}, REDDIT_CLIENT_SECRET_ENV),
        (
            {
                REDDIT_CLIENT_ID_ENV: "client",
                REDDIT_CLIENT_SECRET_ENV: "secret",
                REDDIT_USER_AGENT_ENV: "generic-client",
            },
            REDDIT_USER_AGENT_ENV,
        ),
    ],
)
def test_invalid_configuration(
    environment: dict[str, str], expected_message: str
) -> None:
    with pytest.raises(ConfigError, match=expected_message):
        Settings.from_env(environment)
