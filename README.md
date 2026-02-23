# SOARIX News Bot

Telegram news bot that:
- pulls news from RSS feeds (AI/agents/LLMs)
- rewrites into short Russian Telegram posts via LLM (Ollama or OpenAI)
- schedules up to 6 posts/day
- stores state in SQLite to avoid duplicates

## Quick Start

1) Create and fill `.env`:

```bash
copy .env.example .env
```

2) Install deps:

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
```

3) Run:

```bash
python -m app
```

CLI (optional):

```bash
python -m app.cli fetch
python -m app.cli plan
python -m app.cli queue
```

## Metrics (Telethon Collector)

Telegram Bot API does not provide full per-post analytics for channels.
To collect views/forwards/reactions snapshots you can run a MTProto collector
with Telethon (it logs in as your Telegram user once).

1) Create API credentials: https://my.telegram.org
2) Put in `.env`:
- `TELETHON_API_ID`
- `TELETHON_API_HASH`
- `TELETHON_SESSION`
3) Run collector:

```bash
python -m app.telethon_collector
```

Then in bot chat:
- `/metrics`

## Bot Setup

1) Start the bot in Telegram: `/start`
2) Set a target where to post:
   - in a chat: send `/settarget`
   - or in private: `/settarget @your_channel` or `/settarget -100123...`
3) Plan today queue (optional): `/plan`
4) Optional immediate post: `/postnow`

## Config

Key env vars:
- `TELEGRAM_BOT_TOKEN`
- `POST_TIMES` (default: `09:00,12:00,15:00,18:00,21:00,00:00`)
- LLM backend:
  - Ollama: `OLLAMA_BASE_URL`, `OLLAMA_MODEL`
  - OpenAI: `OPENAI_API_KEY`, `OPENAI_MODEL`

## Notes

- Uses RSS only (no heavy scraping).
- Never commit `.env`.
