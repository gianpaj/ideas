"""Authenticated tweepy.Client factories."""
import tweepy
import config


def make_app_client() -> tweepy.Client:
    """Bearer-token client: user timelines, mentions, user tweets, search."""
    return tweepy.Client(
        bearer_token=config.TWITTER_BEARER_TOKEN,
        wait_on_rate_limit=True,  # sleeps on 429 using x-rate-limit-reset header
    )


def make_user_client() -> tweepy.Client | None:
    """OAuth 1.0a client: liked_tweets endpoint.

    Returns None if OAuth credentials are not configured; the caller
    should skip the likes signal gracefully.
    """
    if not config.OAUTH_AVAILABLE:
        return None
    return tweepy.Client(
        consumer_key=config.TWITTER_API_KEY,
        consumer_secret=config.TWITTER_API_KEY_SECRET,
        access_token=config.TWITTER_ACCESS_TOKEN,
        access_token_secret=config.TWITTER_ACCESS_TOKEN_SECRET,
        wait_on_rate_limit=True,
    )
