import os
from dataclasses import dataclass

from dotenv import load_dotenv


DEFAULT_RSS_FEEDS = [
    "https://openai.com/blog/rss.xml",
    "https://blog.google/technology/ai/rss/",
    "https://deepmind.google/discover/blog/rss.xml",
    "https://huggingface.co/blog/feed.xml",
    "https://www.anthropic.com/news/rss.xml",
]


@dataclass(frozen=True)
class Config:
    telegram_bot_token: str

    # Runtime
    app_mode: str
    dashboard_port: int
    timezone: str

    # Target
    target_chat_id: str

    # Content
    post_times: list[str]
    max_posts_per_day: int
    rss_feeds: list[str]
    lang: str

    # Storage
    db_path: str

    # LLM
    ollama_base_url: str
    ollama_model: str
    openai_api_key: str
    openai_model: str
    llm_timeout_seconds: int
    prefer_ollama: bool
    enable_review: bool

    # Telethon metrics collector
    telethon_api_id: int
    telethon_api_hash: str
    telethon_session: str
    collect_interval_seconds: int
    metrics_recent_limit: int


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in (value or "").split(",") if item.strip()]


def _safe_int(value: str, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _validate_hhmm(values: list[str]) -> list[str]:
    out: list[str] = []
    for raw in values:
        parts = raw.split(":")
        if len(parts) != 2:
            continue
        hh, mm = parts
        if not (hh.isdigit() and mm.isdigit()):
            continue
        h, m = int(hh), int(mm)
        if 0 <= h <= 23 and 0 <= m <= 59:
            out.append(f"{h:02d}:{m:02d}")
    return out


def load_config() -> Config:
    load_dotenv()

    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN is required")

    app_mode = os.getenv("APP_MODE", "bot").strip().lower()
    dashboard_port = _safe_int(os.getenv("DASHBOARD_PORT", "8080"), 8080)
    timezone = os.getenv("TIMEZONE", "UTC").strip() or "UTC"

    post_times_raw = _split_csv(os.getenv("POST_TIMES", "09:00,12:00,15:00,18:00,21:00,00:00"))
    post_times = _validate_hhmm(post_times_raw)[:6]
    if not post_times:
        post_times = ["09:00"]

    max_posts_per_day = min(6, max(1, _safe_int(os.getenv("MAX_POSTS_PER_DAY", os.getenv("POSTS_PER_DAY", "6")), 6)))

    rss_feeds = _split_csv(os.getenv("RSS_FEEDS", ""))
    if not rss_feeds:
        rss_feeds = DEFAULT_RSS_FEEDS

    return Config(
        telegram_bot_token=token,
        app_mode=app_mode,
        dashboard_port=dashboard_port,
        timezone=timezone,
        target_chat_id=os.getenv("TARGET_CHAT_ID", "").strip(),
        post_times=post_times,
        max_posts_per_day=max_posts_per_day,
        rss_feeds=rss_feeds,
        lang=os.getenv("LANG", "ru").strip() or "ru",
        db_path=os.getenv("DB_PATH", "soarix_news.db").strip(),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip().rstrip("/"),
        ollama_model=os.getenv("OLLAMA_MODEL", "qwen3-coder:480b-cloud").strip(),
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo").strip(),
        llm_timeout_seconds=_safe_int(os.getenv("LLM_TIMEOUT_SECONDS", "15"), 15),
        prefer_ollama=os.getenv("PREFER_OLLAMA", "1").strip() not in ("0", "false", "False"),
        enable_review=os.getenv("ENABLE_REVIEW", "0").strip() in ("1", "true", "True"),
        telethon_api_id=_safe_int(os.getenv("TELETHON_API_ID", "0"), 0),
        telethon_api_hash=os.getenv("TELETHON_API_HASH", "").strip(),
        telethon_session=os.getenv("TELETHON_SESSION", "soarix_telethon").strip() or "soarix_telethon",
        collect_interval_seconds=_safe_int(os.getenv("COLLECT_INTERVAL_SECONDS", "600"), 600),
        metrics_recent_limit=_safe_int(os.getenv("METRICS_RECENT_LIMIT", "30"), 30),
    )
