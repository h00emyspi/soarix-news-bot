import os
from dataclasses import dataclass
from dotenv import load_dotenv


load_dotenv()


@dataclass
class Config:
    telegram_bot_token: str
    target_chat_id: str
    post_times: list[str]
    posts_per_day: int

    db_path: str

    ollama_base_url: str
    ollama_model: str

    openai_api_key: str
    openai_model: str

    lang: str


def load_config() -> Config:
    post_times_raw = os.getenv("POST_TIMES", "09:00,12:00,15:00,18:00,21:00,00:00")
    post_times = [t.strip() for t in post_times_raw.split(",") if t.strip()]

    return Config(
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
        target_chat_id=os.getenv("TARGET_CHAT_ID", "").strip(),
        post_times=post_times,
        posts_per_day=int(os.getenv("POSTS_PER_DAY", "6")),
        db_path=os.getenv("DB_PATH", "soarix_news.db").strip(),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip().rstrip("/"),
        ollama_model=os.getenv("OLLAMA_MODEL", "qwen3-coder:480b-cloud").strip(),
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo").strip(),
        lang=os.getenv("LANG", "ru").strip(),
    )
