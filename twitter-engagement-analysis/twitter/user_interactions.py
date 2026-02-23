"""Build a weighted interaction graph for a given user.

Signals collected:
  - Replies authored by the target user (weight 4)
  - Quote-tweets authored by the target user (weight 3)
  - Retweets authored by the target user (weight 2)
  - Incoming mentions of the target user (weight 1)
  - Tweets the target user has liked (weight 1, requires OAuth)
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict

import tweepy

logger = logging.getLogger(__name__)

WEIGHTS = {
    "reply": 4,
    "quote": 3,
    "retweet": 2,
    "mention": 1,
    "like": 1,
}

TWEET_FIELDS = [
    "created_at",
    "author_id",
    "public_metrics",
    "referenced_tweets",
    "in_reply_to_user_id",
    "entities",
]
EXPANSIONS = ["author_id", "referenced_tweets.id", "in_reply_to_user_id"]
USER_FIELDS = ["username", "name", "public_metrics"]


def _classify_tweet(tweet) -> tuple[str, str | None]:
    """Return (interaction_type, target_user_id) for a tweet authored by the tracked user."""
    if not tweet.referenced_tweets:
        return ("original", None)
    for ref in tweet.referenced_tweets:
        if ref.type == "replied_to":
            return ("reply", str(tweet.in_reply_to_user_id) if tweet.in_reply_to_user_id else None)
        if ref.type == "quoted":
            return ("quote", str(ref.id))
        if ref.type == "retweeted":
            return ("retweet", str(ref.id))
    return ("original", None)


def build_interaction_scores(
    user_id: str,
    app_client: tweepy.Client,
    user_client: tweepy.Client | None = None,
    max_own_tweets: int = 800,
    max_mentions: int = 800,
    max_liked: int = 1000,
) -> dict[str, int]:
    """Return a mapping of {twitter_user_id: interaction_score} for all partners.

    Args:
        user_id: Numeric Twitter user ID of the account being analysed.
        app_client: Bearer-token tweepy.Client (for timeline & mentions).
        user_client: OAuth 1.0a tweepy.Client (for liked tweets). May be None.
        max_own_tweets: Maximum number of the user's own tweets to inspect.
        max_mentions: Maximum number of mention tweets to inspect.
        max_liked: Maximum number of liked tweets to inspect.
    """
    scores: dict[str, int] = defaultdict(int)

    # ── Signal 1: own timeline (replies, quotes, retweets) ───────────────────
    logger.info("Fetching own timeline for user %s…", user_id)
    try:
        for response in tweepy.Paginator(
            app_client.get_users_tweets,
            user_id,
            tweet_fields=TWEET_FIELDS,
            expansions=EXPANSIONS,
            user_fields=USER_FIELDS,
            max_results=100,
            limit=max_own_tweets // 100,
        ):
            includes_tweets = {
                str(t.id): t
                for t in (response.includes or {}).get("tweets", [])
            }

            for tweet in response.data or []:
                kind, target_id = _classify_tweet(tweet)
                if kind == "reply" and target_id:
                    scores[target_id] += WEIGHTS["reply"]
                elif kind in ("quote", "retweet") and target_id:
                    ref_tweet = includes_tweets.get(target_id)
                    if ref_tweet and ref_tweet.author_id:
                        scores[str(ref_tweet.author_id)] += WEIGHTS[kind]

            time.sleep(0.5)  # per-second guard
    except tweepy.errors.Forbidden as exc:
        logger.warning("Cannot fetch own timeline (tier restriction?): %s", exc)

    # ── Signal 2: incoming mentions ───────────────────────────────────────────
    logger.info("Fetching mentions for user %s…", user_id)
    try:
        for response in tweepy.Paginator(
            app_client.get_users_mentions,
            user_id,
            tweet_fields=["author_id", "public_metrics"],
            expansions=["author_id"],
            user_fields=["username"],
            max_results=100,
            limit=max_mentions // 100,
        ):
            for tweet in response.data or []:
                if tweet.author_id:
                    scores[str(tweet.author_id)] += WEIGHTS["mention"]
            time.sleep(0.5)
    except tweepy.errors.Forbidden as exc:
        logger.warning("Cannot fetch mentions (tier restriction?): %s", exc)

    # ── Signal 3: liked tweets (OAuth required) ───────────────────────────────
    if user_client is None:
        logger.warning(
            "OAuth 1.0a credentials not configured — skipping liked-tweets signal. "
            "Set TWITTER_API_KEY / ACCESS_TOKEN vars to enable it."
        )
    else:
        logger.info("Fetching liked tweets for user %s…", user_id)
        try:
            for response in tweepy.Paginator(
                user_client.get_liked_tweets,
                user_id,
                tweet_fields=["author_id"],
                expansions=["author_id"],
                max_results=100,
                limit=max_liked // 100,
            ):
                for tweet in response.data or []:
                    if tweet.author_id:
                        scores[str(tweet.author_id)] += WEIGHTS["like"]
                time.sleep(0.5)
        except tweepy.errors.Forbidden as exc:
            logger.warning("Cannot fetch liked tweets: %s", exc)

    # Remove self-interactions
    scores.pop(user_id, None)

    return dict(scores)
