"""Fetch and score the top N tweets for a given user."""
from __future__ import annotations

import logging
import time

import tweepy

logger = logging.getLogger(__name__)


def engagement_score(metrics: dict) -> float:
    """Weighted engagement score for a tweet.

    Weights reflect intentionality:
      - Retweet (3.0): leaves the author's follower graph — strongest virality signal.
      - Quote (2.5): viral + spawns new conversation.
      - Reply (1.5): engagement but could indicate controversy.
      - Like (1.0): low-friction, high-volume baseline.
      - Impression (0.01): scaled way down; raw views dwarf interaction counts.
    """
    return (
        metrics.get("retweet_count", 0) * 3.0
        + metrics.get("quote_count", 0) * 2.5
        + metrics.get("like_count", 0) * 1.0
        + metrics.get("reply_count", 0) * 1.5
        + metrics.get("impression_count", 0) * 0.01
    )


def fetch_top_tweets(
    client: tweepy.Client,
    user_id: str,
    n: int = 3,
    fetch_limit: int = 100,
) -> list[dict]:
    """Return the top n tweets by engagement score for the given user.

    Only original tweets and replies are considered; bare retweets are excluded
    because their engagement metrics belong to the original author.

    Args:
        client: Authenticated tweepy.Client.
        user_id: Numeric Twitter user ID.
        n: Number of top tweets to return.
        fetch_limit: How many recent tweets to scan (max 100 per call without pagination).

    Returns:
        List of dicts sorted by descending engagement score.
    """
    try:
        response = client.get_users_tweets(
            user_id,
            tweet_fields=["public_metrics", "created_at", "text", "entities", "lang"],
            max_results=min(fetch_limit, 100),
            exclude=["retweets"],  # only original content + replies
        )
        time.sleep(1)  # per-second rate-limit guard
    except tweepy.errors.Forbidden as exc:
        logger.warning("Cannot fetch tweets for user %s: %s", user_id, exc)
        return []
    except tweepy.errors.TweepyException as exc:
        logger.error("Tweepy error fetching tweets for user %s: %s", user_id, exc)
        return []

    all_tweets: list[dict] = []
    for tweet in response.data or []:
        m = dict(tweet.public_metrics) if tweet.public_metrics else {}
        all_tweets.append(
            {
                "id": str(tweet.id),
                "text": tweet.text,
                "created_at": str(tweet.created_at),
                "lang": getattr(tweet, "lang", None),
                "metrics": m,
                "score": engagement_score(m),
                "url": f"https://twitter.com/i/web/status/{tweet.id}",
            }
        )

    all_tweets.sort(key=lambda t: t["score"], reverse=True)
    return all_tweets[:n]
