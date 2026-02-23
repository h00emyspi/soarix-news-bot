from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


DEFAULT_FEEDS = [
    "https://venturebeat.com/category/ai/feed/",
    "https://www.marktechpost.com/feed/",
    "https://www.artificialintelligence-news.com/feed/",
]


@dataclass(frozen=True)
class Config:
    telegram_bot_token: str
    db_path: Path
    post_times: list[str]
    rss_feeds: list[str]
    max_posts_per_day: int
    timezone: str
    ollama_base_url: str
    ollama_model: str
    openai_api_key: str
    openai_model: str


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _safe_int(value: str, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _validate_hhmm(values: list[str]) -> list[str]:
    validated: list[str] = []
    for raw in values:
        parts = raw.split(":")
        if len(parts) != 2:
            continue
        hh, mm = parts
        if not (hh.isdigit() and mm.isdigit()):
            continue
        h, m = int(hh), int(mm)
        if 0 <= h <= 23 and 0 <= m <= 59:
            validated.append(f"{h:02d}:{m:02d}")
    return validated


def load_config() -> Config:
    load_dotenv()

    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN is required")

    post_times_raw = _split_csv(os.getenv("POST_TIMES", "09:00,12:00,15:00,18:00,21:00,00:00"))
    post_times = _validate_hhmm(post_times_raw)[:6]
    if not post_times:
        post_times = ["09:00"]

    feeds = _split_csv(os.getenv("RSS_FEEDS", ",".join(DEFAULT_FEEDS)))
    max_posts_per_day = min(6, max(1, _safe_int(os.getenv("MAX_POSTS_PER_DAY", "6"), 6)))

    return Config(
        telegram_bot_token=token,
        db_path=Path(os.getenv("DB_PATH", "bot.db")),
        post_times=post_times,
        rss_feeds=feeds,
        max_posts_per_day=max_posts_per_day,
        timezone=os.getenv("TIMEZONE", "UTC"),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    )
