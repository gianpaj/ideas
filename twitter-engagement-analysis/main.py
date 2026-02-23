"""Twitter/X Engagement Analyser — orchestrator.

Usage:
    python main.py [--clear-cache]

Steps:
  1. Resolve @TARGET_USERNAME → numeric user_id
  2. Build weighted interaction scores (replies, quotes, RTs, mentions, likes)
  3. Select top N interaction partners
  4. Fetch top-3 high-engagement tweets for each partner
  5. Analyse each user's tweets with Claude (per-user prompt)
  6. Synthesise cross-user patterns with Claude (global prompt)
  7. Write output/report_<timestamp>.{json,md}
"""
from __future__ import annotations

import argparse
import logging
import sys

import tweepy

import config
from cache import disk_cache as cache
from twitter.client import make_app_client, make_user_client
from twitter.user_interactions import build_interaction_scores
from twitter.top_tweets import fetch_top_tweets
from ai import analyzer
from report import builder

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")

# Cache TTL constants (hours)
_TTL_SCORES = config.CACHE_TTL_HOURS
_TTL_TWEETS = 6.0
_TTL_ANALYSIS = 48.0


def resolve_user_id(client: tweepy.Client, username: str) -> str:
    cached = cache.get("user_id", username, ttl_hours=168)  # 1 week
    if cached:
        return str(cached)
    response = client.get_user(username=username, user_fields=["public_metrics"])
    if not response.data:
        logger.error("User @%s not found.", username)
        sys.exit(1)
    uid = str(response.data.id)
    cache.set("user_id", username, uid)
    return uid


def resolve_user_objects(client: tweepy.Client, user_ids: list[str]) -> list[dict]:
    """Fetch full user objects for a list of IDs."""
    # Twitter API accepts up to 100 IDs per call
    users = []
    for i in range(0, len(user_ids), 100):
        batch = user_ids[i : i + 100]
        response = client.get_users(
            ids=batch,
            user_fields=["username", "name", "public_metrics", "description"],
        )
        for u in response.data or []:
            users.append(
                {
                    "id": str(u.id),
                    "username": u.username,
                    "name": u.name,
                    "public_metrics": dict(u.public_metrics) if u.public_metrics else {},
                    "description": getattr(u, "description", ""),
                }
            )
    return users


def main() -> None:
    parser = argparse.ArgumentParser(description="Twitter/X engagement analyser")
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear all cached API responses before running",
    )
    args = parser.parse_args()

    if args.clear_cache:
        cache.clear_all()
        logger.info("Cache cleared.")

    app_client = make_app_client()
    user_client = make_user_client()
    if user_client is None:
        logger.warning(
            "OAuth credentials not set — liked-tweets signal disabled. "
            "Set TWITTER_API_KEY / ACCESS_TOKEN in .env to enable it."
        )

    target = config.TARGET_USERNAME
    top_n = config.TOP_N_USERS
    top_tweets_n = config.TOP_N_TWEETS

    # ── Step 1: resolve target user ID ───────────────────────────────────────
    logger.info("Resolving @%s…", target)
    user_id = resolve_user_id(app_client, target)
    logger.info("@%s → ID %s", target, user_id)

    # ── Step 2: build interaction scores ─────────────────────────────────────
    scores: dict[str, int] | None = cache.get("interaction_scores", user_id, _TTL_SCORES)
    if scores is None:
        logger.info("Building interaction graph for @%s…", target)
        scores = build_interaction_scores(user_id, app_client, user_client)
        cache.set("interaction_scores", user_id, scores)
    else:
        logger.info("Loaded interaction scores from cache (%d partners).", len(scores))

    if not scores:
        logger.error("No interaction data found for @%s. Check API tier and credentials.", target)
        sys.exit(1)

    # ── Step 3: select top N interaction partners ─────────────────────────────
    top_ids = sorted(scores, key=lambda uid: scores[uid], reverse=True)[:top_n]
    if len(top_ids) < top_n:
        logger.warning(
            "Only %d interaction partners found (wanted %d).", len(top_ids), top_n
        )

    logger.info("Top %d partners by interaction score: %s", len(top_ids), top_ids[:5])

    # ── Step 4: resolve user objects ─────────────────────────────────────────
    top_users_raw = resolve_user_objects(app_client, top_ids)
    # Attach interaction scores and preserve rank order
    id_to_user = {u["id"]: u for u in top_users_raw}
    top_users: list[dict] = []
    for uid in top_ids:
        user = id_to_user.get(uid)
        if user:
            user["interaction_score"] = scores[uid]
            top_users.append(user)

    # ── Step 5: fetch top tweets for each partner ─────────────────────────────
    for user in top_users:
        uid = user["id"]
        cached_tweets = cache.get("user_top_tweets", uid, _TTL_TWEETS)
        if cached_tweets is not None:
            user["top_tweets"] = cached_tweets
            logger.info("  @%s: top tweets loaded from cache.", user["username"])
        else:
            logger.info("  @%s: fetching top tweets…", user["username"])
            tweets = fetch_top_tweets(app_client, uid, n=top_tweets_n)
            user["top_tweets"] = tweets
            cache.set("user_top_tweets", uid, tweets)

    # ── Step 6: per-user Claude analysis ─────────────────────────────────────
    per_user_analyses: list[dict] = []
    for user in top_users:
        uid = user["id"]
        cached_analysis = cache.get("claude_analysis", uid, _TTL_ANALYSIS)
        if cached_analysis is not None:
            logger.info("  @%s: analysis loaded from cache.", user["username"])
            per_user_analyses.append(cached_analysis)
        else:
            if not user.get("top_tweets"):
                logger.warning("  @%s: no tweets available — skipping analysis.", user["username"])
                continue
            logger.info("  @%s: running Claude per-user analysis…", user["username"])
            analysis = analyzer.per_user_analysis(user, user["top_tweets"])
            per_user_analyses.append(analysis)
            cache.set("claude_analysis", uid, analysis)

    # ── Step 7: global summary ────────────────────────────────────────────────
    global_cache_key = f"{user_id}_global"
    global_summ = cache.get("global_summary", global_cache_key, _TTL_ANALYSIS)
    if global_summ is not None:
        logger.info("Global summary loaded from cache.")
    else:
        logger.info("Running Claude global summary…")
        global_summ = analyzer.global_summary(per_user_analyses, target)
        cache.set("global_summary", global_cache_key, global_summ)

    # ── Step 8: write report ──────────────────────────────────────────────────
    json_path, md_path = builder.build(target, top_users, per_user_analyses, global_summ)
    print(f"\nReport written:\n  JSON: {json_path}\n  Markdown: {md_path}")


if __name__ == "__main__":
    main()
