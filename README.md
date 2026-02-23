# SOARIX News Bot

Telegram news bot + web dashboard:
- pulls news from RSS feeds (AI/agents/LLMs)
- rewrites into short Russian Telegram posts via LLM (Ollama or OpenAI)
- schedules up to 6 posts/day
- stores state in SQLite to avoid duplicates
- has a web dashboard with metrics, controls and API

## Quick Start

1) Create and fill `.env`:

```bash
cp .env.example .env
```

2) Start bot mode:

```bash
bash scripts/run.sh
```

3) Start dashboard mode:

```bash
bash scripts/run.sh dashboard
```

Dashboard URL: `http://localhost:8080`

## Dashboard features

- Metrics: total posted items, posts in last 24h, top sources.
- Recent posts table from SQLite.
- Set `target_chat_id` from web form.
- Manual publish action (`post now`).
- API endpoints:
  - `GET /health`
  - `GET /api/metrics`

## Bot Setup (Telegram)

1) Start the bot in Telegram: `/start`
2) Send `/settarget` in the chat/channel you want to post to (bot must be admin in channels)
3) Optional: `/postnow`
4) Optional: `/status`

## Config

Key env vars:
- `TELEGRAM_BOT_TOKEN`
- `APP_MODE` = `bot` or `dashboard`
- `DASHBOARD_PORT` (default: `8080`)
- `POST_TIMES` (default: `09:00,12:00,15:00,18:00,21:00,00:00`)
- `MAX_POSTS_PER_DAY` (1..6)
- `TIMEZONE` (default: `UTC`)
- `RSS_FEEDS` (comma-separated RSS URLs)
- LLM backend:
  - Ollama: `OLLAMA_BASE_URL`, `OLLAMA_MODEL`
  - OpenAI: `OPENAI_API_KEY`, `OPENAI_MODEL`

## GitHub / CI

GitHub Actions workflow (`.github/workflows/ci.yml`) runs on `push` + `pull_request`:
- installs dependencies,
- compile check (`python -m compileall app`),
- unit tests (`python -m unittest discover -s tests -v`).

## Notes

- Uses RSS only (no heavy scraping).
- Link canonicalization removes tracking params (`utm_*`, `fbclid`, `gclid`) to reduce duplicate posts.
- Publish operations are guarded against concurrent duplicate triggers in bot/dashboard.
- Never commit `.env`.
