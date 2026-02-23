"""Centralized configuration loaded from environment variables."""
import os
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        raise EnvironmentError(
            f"Required environment variable '{key}' is not set. "
            f"Copy .env.example to .env and fill in your credentials."
        )
    return value


def _optional(key: str, default: str) -> str:
    return os.environ.get(key, default)


# Twitter / X
TWITTER_BEARER_TOKEN: str = _require("TWITTER_BEARER_TOKEN")

# OAuth 1.0a — only needed for get_liked_tweets; degrade gracefully if absent
TWITTER_API_KEY: str | None = os.environ.get("TWITTER_API_KEY")
TWITTER_API_KEY_SECRET: str | None = os.environ.get("TWITTER_API_KEY_SECRET")
TWITTER_ACCESS_TOKEN: str | None = os.environ.get("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET: str | None = os.environ.get("TWITTER_ACCESS_TOKEN_SECRET")

OAUTH_AVAILABLE: bool = all(
    [TWITTER_API_KEY, TWITTER_API_KEY_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET]
)

# Anthropic
ANTHROPIC_API_KEY: str = _require("ANTHROPIC_API_KEY")

# Tuning
TARGET_USERNAME: str = _optional("TARGET_USERNAME", "gianpaj")
TOP_N_USERS: int = int(_optional("TOP_N_USERS", "20"))
TOP_N_TWEETS: int = int(_optional("TOP_N_TWEETS", "3"))
CACHE_TTL_HOURS: float = float(_optional("CACHE_TTL_HOURS", "24"))
