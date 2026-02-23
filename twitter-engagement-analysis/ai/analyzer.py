"""Claude-powered engagement analysis.

Two levels of analysis:
  1. per_user_analysis  — analyses one user's top 3 tweets and extracts tactics.
  2. global_summary     — synthesises all 20 per-user analyses into cross-cutting insights.
"""
from __future__ import annotations

import json
import logging

import anthropic

import config

logger = logging.getLogger(__name__)

_client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

# Models
_PER_USER_MODEL = "claude-sonnet-4-6"   # fast + cost-efficient for 20 individual analyses
_GLOBAL_MODEL = "claude-opus-4-6"       # deeper synthesis for the final summary

# ── Per-user ──────────────────────────────────────────────────────────────────

_PER_USER_SYSTEM = """\
You are an expert in social media growth and Twitter/X engagement strategy.
You will be given a Twitter user's profile and their three highest-engagement tweets.
Analyse concisely what made each tweet perform well and extract 3-5 replicable tactics.

Return ONLY valid JSON (no markdown fences) with these keys:
{
  "user_handle": "string",
  "patterns": ["list of engagement patterns observed"],
  "tone": "brief description of the writing tone",
  "content_types": ["list of content types used, e.g. opinion, thread, question, story"],
  "hook_analysis": "how do their tweets grab attention in the first line?",
  "best_practices": ["list of 3-5 actionable best practices derived from these tweets"]
}
"""


def _build_per_user_prompt(user: dict, tweets: list[dict]) -> str:
    tweets_block = "\n\n".join(
        f"Tweet {i + 1} (engagement score {t['score']:.0f}):\n"
        f"Text: {t['text']}\n"
        f"Likes: {t['metrics'].get('like_count', 0)} | "
        f"Retweets: {t['metrics'].get('retweet_count', 0)} | "
        f"Replies: {t['metrics'].get('reply_count', 0)} | "
        f"Quotes: {t['metrics'].get('quote_count', 0)}\n"
        f"Posted: {t['created_at']}\n"
        f"URL: {t.get('url', '')}"
        for i, t in enumerate(tweets)
    )
    followers = (
        user.get("public_metrics", {}).get("followers_count", "N/A")
        if isinstance(user.get("public_metrics"), dict)
        else "N/A"
    )
    return (
        f"User: @{user['username']} ({user.get('name', '')})\n"
        f"Followers: {followers}\n\n"
        f"Top tweets:\n{tweets_block}\n\n"
        "Analyse these tweets. Return only valid JSON."
    )


def per_user_analysis(user: dict, tweets: list[dict]) -> dict:
    """Return a structured engagement analysis for a single user.

    Falls back to a dict with a 'raw_response' key if JSON parsing fails.
    """
    prompt = _build_per_user_prompt(user, tweets)
    try:
        message = _client.messages.create(
            model=_PER_USER_MODEL,
            max_tokens=1024,
            system=_PER_USER_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        text = message.content[0].text.strip()
        # Strip markdown code fences if the model wrapped the JSON
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except json.JSONDecodeError as exc:
        logger.warning("JSON parse failed for @%s: %s", user.get("username"), exc)
        return {"user_handle": user.get("username"), "raw_response": text}
    except anthropic.APIError as exc:
        logger.error("Anthropic API error for @%s: %s", user.get("username"), exc)
        return {"user_handle": user.get("username"), "error": str(exc)}


# ── Global summary ────────────────────────────────────────────────────────────

_GLOBAL_SYSTEM = """\
You are an expert Twitter/X growth strategist.
You will receive per-user engagement analyses for the accounts that @{target} most frequently interacts with.
Identify cross-cutting patterns, the most effective content strategies, and rank the top 5 actionable tactics @{target} could adopt based on what is working for their network.

Return ONLY valid JSON (no markdown fences) with these keys:
{
  "common_patterns": ["patterns that appear across multiple high-performing accounts"],
  "top_tactics": [
    {"tactic": "string", "rationale": "string", "example": "string"}
  ],
  "tone_spectrum": "description of the range of tones that perform well in this network",
  "content_mix_recommendation": "recommended content mix for @{target}",
  "overall_summary": "2-3 paragraph narrative summary of the key learnings"
}
"""


def _build_global_prompt(per_user_analyses: list[dict], target_username: str) -> str:
    block = json.dumps(per_user_analyses, indent=2)
    return (
        f"Here are the analyses for @{target_username}'s top interaction partners:\n\n"
        f"{block}\n\n"
        "Synthesise the cross-cutting insights. Return only valid JSON."
    )


def global_summary(per_user_analyses: list[dict], target_username: str) -> dict:
    """Return a cross-user engagement synthesis for the target account.

    Falls back to a dict with a 'raw_response' key if JSON parsing fails.
    """
    system = _GLOBAL_SYSTEM.replace("{target}", target_username)
    prompt = _build_global_prompt(per_user_analyses, target_username)
    try:
        message = _client.messages.create(
            model=_GLOBAL_MODEL,
            max_tokens=2048,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        text = message.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except json.JSONDecodeError as exc:
        logger.warning("JSON parse failed for global summary: %s", exc)
        return {"raw_response": text}
    except anthropic.APIError as exc:
        logger.error("Anthropic API error during global summary: %s", exc)
        return {"error": str(exc)}
