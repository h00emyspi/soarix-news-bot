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

## Bot Setup

1) Start the bot in Telegram: `/start`
2) Send `/settarget` in the chat/channel you want to post to (bot must be admin in channels)
3) Optional: `/postnow`

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
