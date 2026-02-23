from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .publisher import post_one
from .storage import Storage


async def _post_one_dynamic(storage: Storage):
    target = storage.get_setting("target_chat_id", "").strip()
    if not target:
        return
    await post_one(storage=storage, target_chat_id=target)


def setup_scheduler(*, storage: Storage, post_times: list[str]):
    scheduler = AsyncIOScheduler()

    for t in post_times:
        hh, mm = t.split(":")
        trigger = CronTrigger(hour=int(hh), minute=int(mm))
        scheduler.add_job(_post_one_dynamic, trigger=trigger, kwargs={"storage": storage})

    return scheduler
