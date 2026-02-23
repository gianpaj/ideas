# Twitter/X Engagement Analyser

Identifies the top 20 accounts a given Twitter user most interacts with, fetches their highest-engagement tweets, and uses Claude to extract actionable engagement patterns.

## What it does

1. **Builds an interaction graph** for `@TARGET_USERNAME` by analysing replies, quote-tweets, retweets, incoming mentions, and liked tweets (weighted by intentionality).
2. **Selects the top 20 most-engaged accounts** by interaction score.
3. **Fetches each account's top 3 tweets** ranked by a composite engagement score (retweets × 3 + quotes × 2.5 + replies × 1.5 + likes).
4. **Runs Claude analysis** on each user's tweets to extract tone, hooks, content types, and best practices.
5. **Synthesises cross-user patterns** into a global strategy report.
6. **Writes JSON + Markdown reports** to `output/`.

## Requirements

- Python 3.11+
- **Twitter/X Basic tier** ($100/month) — the Free tier rate limits make the required endpoints unusable.
- Anthropic API key.

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Configure credentials
cp .env.example .env
# Edit .env with your keys
```

## Usage

```bash
python main.py
```

Options:
- `--clear-cache` — discard all cached API responses and run fresh.

## Output

Reports are written to `output/`:
- `report_<timestamp>.json` — machine-readable full report
- `report_<timestamp>.md` — human-readable summary

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `TWITTER_BEARER_TOKEN` | Yes | App-only bearer token (Basic tier) |
| `TWITTER_API_KEY` | No* | OAuth 1.0a consumer key |
| `TWITTER_API_KEY_SECRET` | No* | OAuth 1.0a consumer secret |
| `TWITTER_ACCESS_TOKEN` | No* | OAuth 1.0a access token |
| `TWITTER_ACCESS_TOKEN_SECRET` | No* | OAuth 1.0a access token secret |
| `ANTHROPIC_API_KEY` | Yes | Claude API key |
| `TARGET_USERNAME` | No | Default: `gianpaj` |
| `TOP_N_USERS` | No | Default: `20` |
| `TOP_N_TWEETS` | No | Default: `3` |
| `CACHE_TTL_HOURS` | No | Default: `24` |

\* OAuth credentials enable the liked-tweets signal (+1 weight per liked tweet). The tool runs without them but interaction scoring will be less comprehensive.

## Project Structure

```
twitter-engagement-analysis/
├── main.py                     # Orchestrator
├── config.py                   # Settings from env vars
├── requirements.txt
├── .env.example
├── twitter/
│   ├── client.py               # Tweepy client factories
│   ├── user_interactions.py    # Weighted interaction graph
│   └── top_tweets.py           # Per-user tweet scoring
├── ai/
│   └── analyzer.py             # Claude per-user + global prompts
├── cache/
│   └── disk_cache.py           # JSON file cache with TTL
└── report/
    └── builder.py              # JSON + Markdown report assembly
```

## Caching

All API responses are cached to `.cache/` with configurable TTL:
- Interaction scores: 24h (configurable via `CACHE_TTL_HOURS`)
- Top tweets per user: 6h
- Claude analyses: 48h

Run with `--clear-cache` to force a full refresh.
