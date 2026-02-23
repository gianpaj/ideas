# Implementation Plan: Twitter/X Engagement Analyser

**Status:** Prototype exists — ready for hardening and production readiness
**Last updated:** 2026-02-23
**Branch:** `claude/twitter-engagement-analysis-VuVzH`

---

## 1. What This Tool Does

Given a Twitter/X username, the tool:

1. Fetches the user's recent timeline, incoming mentions, and liked tweets
2. Builds a weighted interaction graph to identify the 20 accounts they engage with most
3. Fetches each partner's 3 highest-engagement tweets
4. Runs per-user Claude analysis to extract tone, hooks, content patterns, and tactics
5. Synthesises cross-user patterns into a global strategy report
6. Writes `output/report_<timestamp>.{json,md}`

**Use case:** A creator or marketer wants to understand what makes their network's best content work, so they can replicate those patterns.

---

## 2. Current State (Prototype)

The prototype is structurally complete and runnable. Files already in place:

```
twitter-engagement-analysis/
├── main.py                     # 8-step orchestrator
├── config.py                   # env var loader with graceful OAuth degradation
├── requirements.txt            # tweepy, anthropic, python-dotenv
├── twitter/
│   ├── client.py               # Bearer + OAuth 1.0a factory functions
│   ├── user_interactions.py    # Weighted signal collection (reply/quote/RT/mention/like)
│   └── top_tweets.py           # Per-user engagement scoring
├── ai/
│   └── analyzer.py             # Per-user (Sonnet) + global (Opus) Claude calls
├── cache/
│   └── disk_cache.py           # MD5-keyed JSON files with TTL
└── report/
    └── builder.py              # JSON + Markdown rendering
```

**What still needs work:**

| Area | Gap |
|---|---|
| API tier handling | Basic tier assumed; no handling for pay-per-use 429 quirks |
| `liked_tweets` endpoint | Known breakage on pay-per-use plan (Feb 2026 bug) |
| `following` endpoint | Not used yet — could improve partner discovery |
| Rate limit robustness | `wait_on_rate_limit=True` on tweepy client helps but not tested at scale |
| Error surface | Some exceptions caught broadly; others could surface silently |
| Tests | No test suite exists |
| Packaging | No `.env.example`, no setup guide beyond README |
| CI / local dev | No Makefile, no linter config, no pre-commit hooks |

---

## 3. API Tier Decision

### Recommendation: Start with **Basic tier ($200/month)**

| Factor | Basic ($200/mo) | Pay-Per-Use (2026) |
|---|---|---|
| Monthly Post reads | ~10,000–15,000 | Unlimited (billed at $0.005/Post) |
| Monthly cost (typical run) | Fixed $200 | ~$2–15 for a full 20-user analysis |
| `liked_tweets` access | Works with OAuth 1.0a | **Broken as of Feb 2026 (429 bug)** |
| Rate limit windows | 15-minute rolling | Same rate limits; only billing differs |
| Predictability | Fixed budget | Variable; good for infrequent use |

**Decision rationale:**

- If running daily for multiple accounts → Basic tier ($200/mo) is more predictable
- If running once a week or ad-hoc → pay-per-use is cheaper (~$2–15/run)
- The `liked_tweets` bug on pay-per-use means the likes signal is currently unreliable there; Basic + OAuth 1.0a is safer today

### Cost estimate per full analysis run

| Operation | Calls | Posts returned | Cost (pay-per-use) |
|---|---|---|---|
| 1× user lookup | 1 | — | $0.01 |
| Own timeline (800 posts) | 8 pages | 800 | $4.00 |
| Mentions (800 posts) | 8 pages | 800 | $4.00 |
| Liked tweets (1000) | 10 pages | 1,000 | $5.00 |
| Top tweets (20 users × 100 fetched) | 20 calls | 2,000 | $10.00 |
| **Total** | | | **~$23.01** |

With caching (24h TTL on scores, 6h on tweets), subsequent runs within the cache window cost ~$0.10 for the Claude API only.

---

## 4. Authentication Architecture

Two clients are needed because no single auth method covers all five endpoints:

```
Bearer Token (App-Only)           OAuth 1.0a User Context
─────────────────────────         ──────────────────────────────
GET /2/users/by/username/:u  ✓    GET /2/users/:id/liked_tweets ✓
GET /2/users/:id/tweets      ✓    (Bearer Token returns HTTP 403)
GET /2/users/:id/mentions    ✓
GET /2/users/:id/following   ✓
```

### Setup in `twitter/client.py`

Already implemented correctly:
- `make_app_client()` — Bearer Token, `wait_on_rate_limit=True`
- `make_user_client()` — OAuth 1.0a, returns `None` if env vars absent

### OAuth 1.0a credentials — what to set in `.env`

```
TWITTER_API_KEY=<consumer key from developer.x.com>
TWITTER_API_KEY_SECRET=<consumer secret>
TWITTER_ACCESS_TOKEN=<access token for @target_username>
TWITTER_ACCESS_TOKEN_SECRET=<access token secret>
```

These are static tokens tied to a single account (the one being analysed). They do not expire unless revoked. This means the tool can only read likes for the **one account whose tokens you hold** — not arbitrary public users.

---

## 5. The Five Endpoints — Implementation Details

### 5.1 `GET /2/users/by/username/:username` — User Lookup

**Used in:** `main.py:resolve_user_id()`

**Current implementation:** Correct. Caches user ID for 1 week (168h).

**Fields requested:** `public_metrics` — gives follower/following counts for the target.

**Rate limit concern:** None at this scale. Single call, ~900 req/15min on Basic.

**Action items:**
- [ ] Also request `description` to pass to Claude for richer context
- [ ] Validate that the returned user is not protected (private) before proceeding — a protected target will yield empty timelines

---

### 5.2 `GET /2/users/:id/tweets` — Own Timeline

**Used in:** `twitter/user_interactions.py:build_interaction_scores()` (Signal 1)
Also in: `twitter/top_tweets.py:fetch_top_tweets()` (for partner tweet fetching)

**Current implementation:** Paginator with `limit=max_own_tweets // 100` (default: 8 pages → 800 posts). Fields: `created_at`, `author_id`, `public_metrics`, `referenced_tweets`, `in_reply_to_user_id`, `entities`.

**Classification logic** (`_classify_tweet`):
- `replied_to` ref → reply (weight 4) to `in_reply_to_user_id`
- `quoted` ref → quote (weight 3) to original author via `includes.tweets`
- `retweeted` ref → retweet (weight 2) to original author via `includes.tweets`

**Rate limit:** ~1,500 req/15min app-level (Bearer). 8 pages at 100 posts = 8 requests. Well within limits.

**Known gap — quote-tweet author resolution:**
The current code looks up the quoted tweet author from `response.includes.tweets`. This only works if the quoted tweet was included in the expansion. If the expansion misses some references (API sometimes omits deleted or restricted tweets), the author goes unscored. This is acceptable degradation.

**Action items:**
- [ ] Add `exclude=["retweets"]` to `fetch_top_tweets` page fetch so retweet metrics aren't double-counted (already done — verify)
- [ ] For the interaction-scoring timeline fetch, do **not** exclude retweets — we want to know who is being retweeted

---

### 5.3 `GET /2/users/:id/mentions` — Incoming Mentions

**Used in:** `twitter/user_interactions.py:build_interaction_scores()` (Signal 2)

**Current implementation:** Paginator, `limit=max_mentions // 100` (8 pages), fields: `author_id`, `public_metrics`, expansions: `author_id`.

**Rate limit:** ~180 req/15min user context, lower than tweets. 8 requests → fine.

**Mention cap:** API only returns the most recent 800 mentions. For active accounts with thousands of mentions this is a recency bias — acceptable.

**Action items:**
- [ ] Add `since_id` support: store the most recent mention ID after each run so subsequent runs only fetch new mentions. This cuts API usage by ~90% on repeat runs.
- [ ] Consider increasing `max_mentions` to the API cap (800) for higher-signal accounts

---

### 5.4 `GET /2/users/:id/liked_tweets` — Liked Tweets

**Used in:** `twitter/user_interactions.py:build_interaction_scores()` (Signal 3)

**Current implementation:** OAuth 1.0a client, paginator with `limit=max_liked // 100` (10 pages), fields: `author_id`, expansions: `author_id`. Degrades gracefully to None if OAuth not configured.

**Critical constraint:** Bearer Token returns HTTP 403. OAuth 1.0a required. Implemented correctly.

**Known Feb 2026 bug on pay-per-use plan:** The endpoint returns 429 errors on pay-per-use regardless of actual rate limit state. Not a problem on Basic tier.

**Mitigation for pay-per-use users:**
```python
# In user_interactions.py, catch the 429 specifically and log clearly:
except tweepy.errors.TooManyRequests as exc:
    logger.warning(
        "liked_tweets returned 429 — known pay-per-use bug (Feb 2026). "
        "Skipping likes signal. Switch to Basic tier or wait for X to fix."
    )
```

**Action items:**
- [ ] Add specific `TooManyRequests` catch with descriptive message (not just `Forbidden`)
- [ ] Add `since_id` incremental fetching (same as mentions — store last-seen like ID)
- [ ] Document in README that this signal requires Basic tier or verified pay-per-use access

---

### 5.5 `GET /2/users/:id/following` — Following List

**Not currently used.** This endpoint would enable a "following overlap" signal — identifying which accounts your target follows AND engages with, which is a strong intentionality signal.

**Rate limit constraint: 15 req/15min** — the most restrictive endpoint. For a user following 2,000 accounts at 1,000 per page, that's 2 requests, well within the limit. For 15,000 follows it becomes 15 requests — hitting the ceiling.

**Potential use:**
```
following_overlap_score = interaction_score × (2 if uid in following_list else 1)
```

Accounts you both interact with AND follow are amplified. This would improve signal quality at the cost of one extra API call per analysis.

**Action items:**
- [ ] Implement `fetch_following_ids(user_id, app_client)` in `twitter/user_interactions.py`
- [ ] Add `INCLUDE_FOLLOWING_SIGNAL` env var (default `false`) to opt in
- [ ] Cache the following list separately with a longer TTL (72h — follows don't change frequently)
- [ ] Handle the `protected` account case (returns 403)

---

## 6. Weighted Interaction Scoring — Current Model

```python
WEIGHTS = {
    "reply": 4,      # intentional, directed, requires effort
    "quote": 3,      # viral signal + own commentary
    "retweet": 2,    # endorsement, leaves your graph
    "mention": 1,    # someone mentioned you (lower intent)
    "like": 1,       # low-friction, high volume
}
```

**Proposed enhancement — following overlap multiplier:**

```python
# After collecting raw scores:
if following_ids:
    for uid in scores:
        if uid in following_ids:
            scores[uid] = int(scores[uid] * 1.5)  # 50% boost for followed accounts
```

This prevents high-volume mention spam from low-intent accounts from outranking deliberate engagement with followed peers.

---

## 7. Rate Limit Strategy

### Current approach
`wait_on_rate_limit=True` on both tweepy clients. Tweepy reads `x-rate-limit-reset` header and sleeps accordingly. Also has `time.sleep(0.5)` guards inside pagination loops.

### Per-endpoint budget for a full analysis run

| Signal | Endpoint | Pages | Requests | Budget (Basic) | Time at limit |
|---|---|---|---|---|---|
| Own timeline | `GET /2/users/:id/tweets` | 8 | 8 | 1,500/15min | < 1s |
| Mentions | `GET /2/users/:id/mentions` | 8 | 8 | 180/15min | < 1s |
| Liked tweets | `GET /2/users/:id/liked_tweets` | 10 | 10 | ~75/15min | < 1s |
| Partner tweets | `GET /2/users/:id/tweets` | 20 | 20 | 1,500/15min | < 1s |
| User lookups (batch) | `GET /2/users` | 1 | 1 | ~300/15min | negligible |

**All signals fit comfortably within a single 15-minute window on Basic tier.**

The following endpoint (if added) at 15 req/15min needs care but 1–2 requests for typical accounts is fine.

### Backoff implementation

Add an explicit backoff wrapper for transient errors (5xx, network):

```python
import time, functools

def with_backoff(fn, max_retries=4):
    """Retry with exponential backoff on network/server errors."""
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except (tweepy.errors.TwitterServerError, Exception) as exc:
            if attempt == max_retries:
                raise
            wait = 2 ** attempt  # 1s, 2s, 4s, 8s
            logger.warning("Attempt %d failed: %s. Retrying in %ds.", attempt + 1, exc, wait)
            time.sleep(wait)
```

---

## 8. Caching Strategy

### Current TTL values

| Namespace | TTL | Rationale |
|---|---|---|
| `user_id` | 168h (1 week) | Usernames rarely change |
| `interaction_scores` | 24h (configurable) | Daily refresh is sufficient for strategy |
| `user_top_tweets` | 6h | New high-engagement tweets don't appear hourly |
| `claude_analysis` | 48h | Analysis output is deterministic given same tweets |
| `global_summary` | 48h | Synthesis of the above |

### Proposed additions

| Namespace | TTL | When to add |
|---|---|---|
| `following_ids` | 72h | When following signal is implemented |
| `mentions_since_id` | permanent | Cursor for incremental mention fetching |
| `likes_since_id` | permanent | Cursor for incremental likes fetching |

### Cache key scheme
Current: `MD5(namespace:identifier)` → `.cache/<hash>.json`

This is opaque but collision-resistant. A human-readable index file (`.cache/index.json`) would help debugging but is not required.

---

## 9. Claude Integration

### Models in use

| Stage | Model | Max tokens | Rationale |
|---|---|---|---|
| Per-user analysis (×20) | `claude-sonnet-4-6` | 1,024 | Cost-efficient; structured JSON output |
| Global synthesis (×1) | `claude-opus-4-6` | 2,048 | Deeper cross-cutting insight |

### Per-user prompt structure

**System:** "You are an expert in Twitter/X engagement strategy. Return only valid JSON."

**User:** User profile + top 3 tweets with metrics + "Analyse these tweets."

**Output schema:**
```json
{
  "user_handle": "string",
  "patterns": ["..."],
  "tone": "string",
  "content_types": ["opinion", "thread", ...],
  "hook_analysis": "string",
  "best_practices": ["...", "...", "..."]
}
```

### Global synthesis prompt

**System:** "You are a Twitter/X growth strategist for @{target}. Return only valid JSON."

**User:** Array of 20 per-user analysis JSON objects.

**Output schema:**
```json
{
  "common_patterns": ["..."],
  "top_tactics": [{"tactic": "...", "rationale": "...", "example": "..."}],
  "tone_spectrum": "string",
  "content_mix_recommendation": "string",
  "overall_summary": "2-3 paragraphs"
}
```

### JSON robustness

Current code strips markdown fences. Already handles `JSONDecodeError` gracefully with `raw_response` fallback.

**Improvement:** Use Anthropic's tool use / structured output (JSON schema enforcement) to eliminate the parse-failure risk entirely:

```python
message = _client.messages.create(
    model=_PER_USER_MODEL,
    max_tokens=1024,
    system=_PER_USER_SYSTEM,
    messages=[{"role": "user", "content": prompt}],
    tools=[{
        "name": "submit_analysis",
        "description": "Submit the engagement analysis result",
        "input_schema": {
            "type": "object",
            "properties": {
                "user_handle": {"type": "string"},
                "patterns": {"type": "array", "items": {"type": "string"}},
                # ...
            },
            "required": ["user_handle", "patterns", "tone", "content_types",
                         "hook_analysis", "best_practices"]
        }
    }],
    tool_choice={"type": "tool", "name": "submit_analysis"}
)
result = message.content[0].input  # already a dict, no JSON parsing needed
```

This eliminates JSON parse failures entirely and is a clean improvement.

### Anthropic cost estimate per run

| Stage | Calls | ~Input tokens | ~Output tokens | Cost |
|---|---|---|---|---|
| Per-user analysis | 20 | 20 × 400 = 8,000 | 20 × 300 = 6,000 | ~$0.10 |
| Global synthesis | 1 | ~6,000 | ~800 | ~$0.05 |
| **Total** | | | | **~$0.15** |

Very affordable. Caching `claude_analysis` for 48h means repeated runs are essentially free for the AI step.

---

## 10. Engagement Scoring Formula

### `top_tweets.py` — current formula

```python
score = retweets × 3.0 + quotes × 2.5 + likes × 1.0 + replies × 1.5 + impressions × 0.01
```

Impressions are only available for the authenticated account owner (requires OAuth + `non_public_metrics`). For partner accounts, impressions will always be 0. This is intentional — the formula degrades gracefully.

**Improvement:** Normalise by follower count to surface punching-above-weight tweets:

```python
def engagement_rate(metrics: dict, followers: int) -> float:
    raw = engagement_score(metrics)
    return raw / max(followers, 1) * 1000  # per 1,000 followers
```

This surfaces a 10,000-follower account's tweet that got 500 likes (5% ER) over a 1M-follower account's tweet that got 2,000 likes (0.2% ER). More useful for understanding what *works* vs. what benefits from distribution scale.

---

## 11. Output Reports

### Current JSON structure

```json
{
  "generated_at": "2026-02-23T10:00:00Z",
  "target_user": "@gianpaj",
  "top_interaction_partners": [
    {
      "rank": 1,
      "username": "...",
      "name": "...",
      "interaction_score": 42,
      "followers": 15230,
      "top_tweets": [...],
      "analysis": {...}
    }
  ],
  "global_summary": {...}
}
```

### Markdown report sections

1. **Overall Strategy & Key Learnings** — global summary narrative
2. **Top 5 Tactics** — ranked, with rationale and example
3. **Common Patterns** — bullet list
4. **Tone spectrum + content mix recommendation**
5. **Per-user breakdown** (×20) — score, hook style, tone, top tweets

### Proposed addition: HTML report

A single-file HTML report with expandable sections per user would be more shareable than Markdown. Low priority but high value for non-technical users.

---

## 12. Error Handling & Graceful Degradation

### Current behaviour by failure mode

| Failure | Current handling | Desired |
|---|---|---|
| User not found | `sys.exit(1)` | ✓ acceptable |
| Bearer Token invalid | Tweepy raises `Unauthorized` — crashes | Add startup validation call |
| Timeline fetch forbidden (Free tier) | Logged as warning, scores empty | ✓ acceptable |
| Mention fetch forbidden | Logged as warning | ✓ acceptable |
| Likes 429 (pay-per-use bug) | Caught as generic `Forbidden` | Add specific `TooManyRequests` catch |
| Claude API error | Returns `{"error": str(exc)}` | ✓ acceptable |
| Claude JSON parse failure | Returns `{"raw_response": text}` | Migrate to tool use (no failures) |
| No interaction partners found | `sys.exit(1)` | ✓ acceptable |

### Startup validation (to add)

```python
def validate_credentials(app_client: tweepy.Client) -> None:
    """Fail fast with a clear message if Bearer Token is invalid."""
    try:
        app_client.get_user(username="twitter")  # canary call
    except tweepy.errors.Unauthorized:
        logger.error("TWITTER_BEARER_TOKEN is invalid or expired.")
        sys.exit(1)
    except tweepy.errors.Forbidden:
        logger.error("Bearer Token does not have sufficient permissions.")
        sys.exit(1)
```

---

## 13. Missing Files to Create

### `.env.example`

```bash
# Required
TWITTER_BEARER_TOKEN=your_bearer_token_here
ANTHROPIC_API_KEY=your_anthropic_key_here

# Optional: enables liked-tweets signal (OAuth 1.0a)
TWITTER_API_KEY=
TWITTER_API_KEY_SECRET=
TWITTER_ACCESS_TOKEN=
TWITTER_ACCESS_TOKEN_SECRET=

# Tuning (defaults shown)
TARGET_USERNAME=gianpaj
TOP_N_USERS=20
TOP_N_TWEETS=3
CACHE_TTL_HOURS=24
```

### `.gitignore` additions

```
.env
.cache/
output/
```

### `Makefile`

```makefile
.PHONY: install run clean-cache lint

install:
	pip install -r requirements.txt

run:
	python main.py

run-fresh:
	python main.py --clear-cache

lint:
	ruff check . && ruff format --check .

clean-cache:
	rm -rf .cache/
```

---

## 14. Testing Strategy

The tool is I/O-heavy (Twitter API + Claude API), so the test pyramid should be:

### Unit tests (pure logic — no mocking needed)

- `test_engagement_score`: verify formula with known inputs
- `test_classify_tweet`: verify reply/quote/retweet classification for all ref types
- `test_cache_ttl`: write cache entry with back-dated timestamp, confirm expiry
- `test_markdown_renderer`: snapshot test on known `report` dict → expected Markdown

### Integration tests (mock tweepy + Anthropic)

- `test_build_interaction_scores_no_oauth`: confirm graceful degradation when `user_client=None`
- `test_build_interaction_scores_liked_tweets_403`: confirm 429/403 is swallowed with warning
- `test_full_pipeline_cached`: run main() with all cache pre-populated, assert report files written

### Framework: `pytest` + `unittest.mock`

```python
# Example: test classification
from twitter.user_interactions import _classify_tweet

def test_classify_reply(mock_tweet):
    mock_tweet.referenced_tweets = [MagicMock(type="replied_to")]
    mock_tweet.in_reply_to_user_id = 12345
    kind, target = _classify_tweet(mock_tweet)
    assert kind == "reply"
    assert target == "12345"
```

---

## 15. Implementation Order

Prioritised by value / risk:

| Priority | Task | File(s) | Effort |
|---|---|---|---|
| P0 | Create `.env.example` | new | 5 min |
| P0 | Add `.gitignore` | new | 5 min |
| P1 | `TooManyRequests` catch for liked_tweets | `twitter/user_interactions.py` | 15 min |
| P1 | Startup credential validation | `main.py` | 20 min |
| P1 | Migrate Claude calls to tool use (no JSON parse failures) | `ai/analyzer.py` | 45 min |
| P2 | `since_id` incremental fetching (mentions + likes) | `twitter/user_interactions.py` | 1h |
| P2 | `engagement_rate` normalised scoring | `twitter/top_tweets.py` | 30 min |
| P2 | Unit test suite (4 tests) | `tests/` | 2h |
| P3 | Following signal with `INCLUDE_FOLLOWING_SIGNAL` flag | `twitter/user_interactions.py` | 2h |
| P3 | HTML report output | `report/builder.py` | 2h |
| P4 | Makefile + ruff config | new | 30 min |

---

## 16. Known Risks & Open Questions

| Risk | Likelihood | Mitigation |
|---|---|---|
| `liked_tweets` 429 bug persists on pay-per-use | Medium | Use Basic tier; add clear error message |
| Target account is protected (private) | Low | Detect and exit with clear message |
| Following list > 15,000 (rate limit hit) | Low | Paginate over multiple 15-min windows; cache aggressively |
| Claude returns malformed JSON | Low | Migrate to tool use (eliminates entirely) |
| X API pricing changes again | Medium | Abstract API tier in config; monitor devcommunity.x.com |
| OAuth tokens revoked by user | Very low | Document re-generation steps in README |

---

## 17. Environment & Prerequisites

- Python 3.11+
- Twitter/X Basic tier ($200/month) **or** pay-per-use credits (~$23/full run)
- Anthropic API key (~$0.15/run)
- OAuth 1.0a tokens for `@TARGET_USERNAME` (enables likes signal)
- All credentials in `.env` (never committed)

---

## 18. API Reference Cheatsheet

| Endpoint | Auth | Rate limit (Basic) | Notes |
|---|---|---|---|
| `GET /2/users/by/username/:u` | Bearer | 900/15min | Single user lookup |
| `GET /2/users` | Bearer | 300/15min | Batch up to 100 IDs |
| `GET /2/users/:id/tweets` | Bearer | 1,500/15min | Max 3,200 posts |
| `GET /2/users/:id/mentions` | Bearer | 180/15min | Max 800 mentions |
| `GET /2/users/:id/liked_tweets` | **OAuth 1.0a only** | ~75/15min | 403 if Bearer Token used |
| `GET /2/users/:id/following` | Bearer (public) | **15/15min** | Most restrictive |

Rate limits are per 15-minute rolling window. Always check `x-rate-limit-remaining` response header as authoritative source.
