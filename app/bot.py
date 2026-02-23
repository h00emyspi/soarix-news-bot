from __future__ import annotations

import asyncio
import logging
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import Config
from app.db import Database
from app.llm import LLMRewriter
from app.rss import NewsItem, fetch_news

LOGGER = logging.getLogger(__name__)


class NewsBotApp:
    def __init__(self, config: Config):
        self.config = config
        self.db = Database(config.db_path)
        self.bot = Bot(token=config.telegram_bot_token)
        self.dp = Dispatcher()
        self.scheduler = AsyncIOScheduler(timezone=config.timezone)
        self.rewriter = LLMRewriter(config)
        self._publish_lock = asyncio.Lock()

        self._register_handlers()
        self._register_jobs()

    def _register_handlers(self) -> None:
        @self.dp.message(Command("start"))
        async def cmd_start(message: Message) -> None:
            await message.answer(
                "Привет! Я новостной бот.\n"
                "Команды:\n"
                "/settarget — назначить текущий чат как цель для постинга\n"
                "/postnow — опубликовать новость сейчас\n"
                "/status — показать текущие настройки"
            )

        @self.dp.message(Command("settarget"))
        async def cmd_settarget(message: Message) -> None:
            chat_id = message.chat.id
            self.db.set_setting("target_chat_id", str(chat_id))
            await message.answer(f"Целевой чат сохранён: <code>{chat_id}</code>")

        @self.dp.message(Command("status"))
        async def cmd_status(message: Message) -> None:
            target_chat = self.db.get_setting("target_chat_id") or "не задан"
            await message.answer(
                "Текущая конфигурация:\n"
                f"- target_chat_id: <code>{target_chat}</code>\n"
                f"- timezone: <code>{self.config.timezone}</code>\n"
                f"- post_times: <code>{', '.join(self.config.post_times[: self.config.max_posts_per_day])}</code>"
            )

        @self.dp.message(Command("postnow"))
        async def cmd_post_now(message: Message) -> None:
            sent = await self.publish_one_news()
            if sent:
                await message.answer("✅ Новость опубликована")
            else:
                await message.answer("ℹ️ Нет новых новостей для публикации")

    def _register_jobs(self) -> None:
        for index, hhmm in enumerate(self.config.post_times[: self.config.max_posts_per_day]):
            hour, minute = hhmm.split(":", 1)
            self.scheduler.add_job(
                self.publish_one_news,
                trigger=CronTrigger(hour=int(hour), minute=int(minute), timezone=self.config.timezone),
                id=f"daily_post_{index}",
                replace_existing=True,
                misfire_grace_time=300,
                coalesce=True,
                max_instances=1,
            )

    def _pick_next_unseen(self, items: list[NewsItem]) -> Optional[NewsItem]:
        for item in items:
            if self.db.is_seen(item.link):
                continue
            if self.db.is_seen_title_source(item.title, item.source):
                continue
            return item
        return None

    async def publish_one_news(self) -> bool:
        async with self._publish_lock:
            target_chat = self.db.get_setting("target_chat_id")
            if not target_chat:
                LOGGER.warning("Target chat is not set. Use /settarget first.")
                return False

            items = await asyncio.to_thread(fetch_news, self.config.rss_feeds)
            next_item = self._pick_next_unseen(items)
            if not next_item:
                return False

            text = await asyncio.to_thread(self.rewriter.rewrite, next_item)
            post = f"{text}\n\n🔗 {next_item.link}"

            try:
                await self.bot.send_message(chat_id=int(target_chat), text=post, disable_web_page_preview=False)
            except Exception as exc:
                LOGGER.exception("Failed to send message: %s", exc)
                return False

            self.db.mark_seen(next_item.link, next_item.title, next_item.source, next_item.published)
            return True

    async def run(self) -> None:
        self.scheduler.start()
        try:
            await self.dp.start_polling(self.bot)
        finally:
            self.scheduler.shutdown(wait=False)
            await self.bot.session.close()
