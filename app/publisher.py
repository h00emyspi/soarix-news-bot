import html
from datetime import datetime, timezone

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from .config import load_config
from .llm import LLM
from .planner import ensure_daily_queue
from .storage import Storage


def _html_post(text: str) -> str:
    # Keep it safe for HTML parse mode.
    return html.escape(text or "")


def _today_utc() -> str:
    return datetime.now(timezone.utc).date().isoformat()


async def post_scheduled(*, storage: Storage, slot: str) -> tuple[bool, str]:
    cfg = load_config()
    if not cfg.telegram_bot_token:
        return False, "TELEGRAM_BOT_TOKEN missing"

    target = storage.get_setting("target_chat_id", "").strip() or cfg.target_chat_id
    if not target:
        return False, "target_chat_id not set"

    day = _today_utc()
    ensure_daily_queue(storage=storage, cfg=cfg)

    q = storage.get_queue_slot(day, slot)
    if not q:
        return False, "no planned slot"
    if q.get("status") == "posted":
        return False, "already posted"

    item = storage.get_item(q["guid"])
    if not item:
        storage.mark_queue_error(day=day, slot=slot, error="item not found")
        return False, "item not found"

    text = (q.get("post_text") or "").strip()
    if not text:
        # fallback
        llm = LLM(
            ollama_base_url=cfg.ollama_base_url,
            ollama_model=cfg.ollama_model,
            openai_api_key=cfg.openai_api_key,
            openai_model=cfg.openai_model,
            timeout_seconds=cfg.llm_timeout_seconds,
            prefer_ollama=cfg.prefer_ollama,
        )
        text = llm.rewrite_news(
            title=item["title"],
            source=item["source"],
            link=item["link"],
            summary=item["summary"],
            lang=cfg.lang,
        )

    bot = Bot(token=cfg.telegram_bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    try:
        msg = await bot.send_message(chat_id=target, text=_html_post(text))
        storage.mark_queue_posted(day=day, slot=slot, tg_message_id=msg.message_id)
        storage.mark_posted(item["guid"], text)
        return True, str(msg.message_id)
    except Exception as e:
        storage.mark_queue_error(day=day, slot=slot, error=str(e))
        return False, str(e)
    finally:
        await bot.session.close()


async def post_one(*, storage: Storage, target_chat_id: str) -> tuple[bool, str]:
    cfg = load_config()
    if not cfg.telegram_bot_token:
        return False, "TELEGRAM_BOT_TOKEN missing"

    # manual: post the newest unposted item now
    ensure_daily_queue(storage=storage, cfg=cfg)
    item = storage.pick_next_unposted()
    if not item:
        return False, "no unposted items"

    llm = LLM(
        ollama_base_url=cfg.ollama_base_url,
        ollama_model=cfg.ollama_model,
        openai_api_key=cfg.openai_api_key,
        openai_model=cfg.openai_model,
        timeout_seconds=cfg.llm_timeout_seconds,
        prefer_ollama=cfg.prefer_ollama,
    )
    rewritten = llm.rewrite_news(title=item["title"], source=item["source"], link=item["link"], summary=item["summary"], lang=cfg.lang)

    bot = Bot(token=cfg.telegram_bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    msg = await bot.send_message(chat_id=target_chat_id, text=_html_post(rewritten))
    await bot.session.close()

    storage.mark_posted(item["guid"], rewritten)
    return True, str(msg.message_id)
