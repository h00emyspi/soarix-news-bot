from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .publisher import post_scheduled
from .storage import Storage


async def _post_slot(storage: Storage, slot: str):
    await post_scheduled(storage=storage, slot=slot)


def setup_scheduler(*, storage: Storage, post_times: list[str]):
    scheduler = AsyncIOScheduler()

    for t in post_times:
        hh, mm = t.split(":")
        trigger = CronTrigger(hour=int(hh), minute=int(mm))
        scheduler.add_job(_post_slot, trigger=trigger, kwargs={"storage": storage, "slot": t})

    return scheduler
