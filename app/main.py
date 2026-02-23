import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from .bot_handlers import router
from .config import Config
from .scheduler import setup_scheduler
from .storage import Storage


def run_bot(cfg: Config):
    storage = Storage(cfg.db_path)
    if cfg.target_chat_id:
        storage.set_setting("target_chat_id", cfg.target_chat_id)

    async def runner():
        bot = Bot(token=cfg.telegram_bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        dp = Dispatcher()

        dp.include_router(router)
        dp["storage"] = storage

        sched = setup_scheduler(storage=storage, post_times=cfg.post_times[: cfg.max_posts_per_day], timezone=cfg.timezone)
        sched.start()

        await dp.start_polling(bot)

    asyncio.run(runner())
