"""Assemble per-user summaries and global summary into JSON + Markdown reports."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_OUTPUT_DIR = Path(__file__).parent.parent / "output"
_OUTPUT_DIR.mkdir(exist_ok=True)


def build(
    target_username: str,
    top_users: list[dict],
    per_user_analyses: list[dict],
    summary: dict,
) -> tuple[Path, Path]:
    """Write JSON and Markdown report files and return their paths.

    Args:
        target_username: Handle being analysed (e.g. "gianpaj").
        top_users: List of user dicts from the Twitter API (username, name, public_metrics, score).
        per_user_analyses: One dict per user from ai.analyzer.per_user_analysis().
        summary: Dict from ai.analyzer.global_summary().

    Returns:
        (json_path, markdown_path)
    """
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    analysis_by_handle = {a.get("user_handle", ""): a for a in per_user_analyses}

    partners = []
    for rank, user in enumerate(top_users, start=1):
        handle = user.get("username", "")
        partners.append(
            {
                "rank": rank,
                "username": handle,
                "name": user.get("name", ""),
                "interaction_score": user.get("interaction_score", 0),
                "followers": (
                    user.get("public_metrics", {}).get("followers_count")
                    if isinstance(user.get("public_metrics"), dict)
                    else None
                ),
                "top_tweets": user.get("top_tweets", []),
                "analysis": analysis_by_handle.get(handle, {}),
            }
        )

    report = {
        "generated_at": ts,
        "target_user": f"@{target_username}",
        "top_interaction_partners": partners,
        "global_summary": summary,
    }

    json_path = _OUTPUT_DIR / f"report_{ts}.json"
    md_path = _OUTPUT_DIR / f"report_{ts}.md"

    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    md_path.write_text(_to_markdown(report))

    logger.info("Report written to %s and %s", json_path, md_path)
    return json_path, md_path


def _to_markdown(report: dict) -> str:
    lines: list[str] = []
    target = report["target_user"]
    ts = report["generated_at"]

    lines += [
        f"# Twitter Engagement Analysis: {target}",
        f"_Generated {ts}_",
        "",
        "---",
        "",
    ]

    # ── Global summary first ─────────────────────────────────────────────────
    gs = report.get("global_summary", {})
    if gs:
        lines += ["## Overall Strategy & Key Learnings", ""]
        if "overall_summary" in gs:
            lines += [gs["overall_summary"], ""]
        if "top_tactics" in gs:
            lines += ["### Top 5 Tactics to Adopt", ""]
            for i, tactic in enumerate(gs.get("top_tactics", []), start=1):
                lines += [
                    f"**{i}. {tactic.get('tactic', '')}**",
                    f"- Rationale: {tactic.get('rationale', '')}",
                    f"- Example: _{tactic.get('example', '')}_",
                    "",
                ]
        if "common_patterns" in gs:
            lines += ["### Common Patterns", ""]
            for p in gs.get("common_patterns", []):
                lines += [f"- {p}"]
            lines += [""]
        if "tone_spectrum" in gs:
            lines += [f"**Tone spectrum:** {gs['tone_spectrum']}", ""]
        if "content_mix_recommendation" in gs:
            lines += [f"**Content mix recommendation:** {gs['content_mix_recommendation']}", ""]
        lines += ["---", ""]

    # ── Per-user sections ────────────────────────────────────────────────────
    lines += ["## Top 20 Interaction Partners", ""]
    for partner in report.get("top_interaction_partners", []):
        rank = partner["rank"]
        handle = partner["username"]
        name = partner.get("name", "")
        score = partner.get("interaction_score", 0)
        followers = partner.get("followers")
        followers_str = f"{followers:,}" if followers is not None else "N/A"

        lines += [
            f"### {rank}. @{handle} — {name}",
            f"_Interaction score: {score} | Followers: {followers_str}_",
            "",
        ]

        analysis = partner.get("analysis", {})
        if analysis.get("hook_analysis"):
            lines += [f"**Hook style:** {analysis['hook_analysis']}", ""]
        if analysis.get("tone"):
            lines += [f"**Tone:** {analysis['tone']}", ""]
        if analysis.get("content_types"):
            lines += [f"**Content types:** {', '.join(analysis['content_types'])}", ""]
        if analysis.get("patterns"):
            lines += ["**Patterns:**"]
            for p in analysis["patterns"]:
                lines += [f"- {p}"]
            lines += [""]
        if analysis.get("best_practices"):
            lines += ["**Best practices:**"]
            for bp in analysis["best_practices"]:
                lines += [f"- {bp}"]
            lines += [""]

        for i, tweet in enumerate(partner.get("top_tweets", []), start=1):
            m = tweet.get("metrics", {})
            lines += [
                f"#### Tweet {i} (score {tweet.get('score', 0):.0f})",
                f"> {tweet.get('text', '').replace(chr(10), ' ')}",
                "",
                f"Likes: {m.get('like_count', 0)} | "
                f"RTs: {m.get('retweet_count', 0)} | "
                f"Replies: {m.get('reply_count', 0)} | "
                f"Quotes: {m.get('quote_count', 0)}",
                f"[View tweet]({tweet.get('url', '')})",
                "",
            ]

        lines += ["---", ""]

    return "\n".join(lines)
