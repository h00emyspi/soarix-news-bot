import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from .bot_handlers import router
from .config import load_config
from .scheduler import setup_scheduler
from .storage import Storage


def main():
    cfg = load_config()
    if not cfg.telegram_bot_token:
        raise SystemExit("TELEGRAM_BOT_TOKEN is required")

    storage = Storage(cfg.db_path)
    if cfg.target_chat_id:
        storage.set_setting("target_chat_id", cfg.target_chat_id)

    async def runner():
        bot = Bot(token=cfg.telegram_bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        dp = Dispatcher()

        # Inject storage into handlers
        dp.include_router(router)
        dp["storage"] = storage

        sched = setup_scheduler(storage=storage, post_times=cfg.post_times[: cfg.posts_per_day])
        sched.start()

        await dp.start_polling(bot)

    asyncio.run(runner())
