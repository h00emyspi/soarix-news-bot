import html

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from .config import load_config
from .llm import LLM
from .news import fetch_feeds
from .storage import Storage


def _html_post(text: str) -> str:
    # Keep it safe for HTML parse mode.
    return html.escape(text or "")


async def post_one(*, storage: Storage, target_chat_id: str) -> tuple[bool, str]:
    cfg = load_config()
    if not cfg.telegram_bot_token:
        return False, "TELEGRAM_BOT_TOKEN missing"

    fetch_feeds(storage)
    item = storage.pick_next_unposted()
    if not item:
        return False, "no unposted items"

    llm = LLM(
        ollama_base_url=cfg.ollama_base_url,
        ollama_model=cfg.ollama_model,
        openai_api_key=cfg.openai_api_key,
        openai_model=cfg.openai_model,
    )
    rewritten = llm.rewrite_news(
        title=item["title"],
        source=item["source"],
        link=item["link"],
        summary=item["summary"],
        lang=cfg.lang,
    )

    bot = Bot(token=cfg.telegram_bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await bot.send_message(chat_id=target_chat_id, text=_html_post(rewritten))
    await bot.session.close()

    storage.mark_posted(item["guid"], rewritten)
    return True, item["guid"]
