from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from datetime import datetime

from .publisher import post_one
from .planner import ensure_daily_queue
from .config import load_config
from .storage import Storage


router = Router()


@router.message(Command("start"))
async def start_cmd(message: Message, storage: Storage):
    await message.answer(
        "SOARIX News Bot\n\n"
        "Команды:\n"
        "/settarget - установить чат/канал для автопостинга\n"
        "/postnow - опубликовать 1 пост сейчас\n"
        "/status - статус\n"
    )


@router.message(Command("settarget"))
async def settarget_cmd(message: Message, storage: Storage):
    parts = (message.text or "").split()
    if len(parts) >= 2:
        target = parts[1].strip()
    else:
        target = str(message.chat.id)

    storage.set_setting("target_chat_id", target)
    await message.answer(f"OK. TARGET_CHAT_ID = {target}")


@router.message(Command("status"))
async def status_cmd(message: Message, storage: Storage):
    target = storage.get_setting("target_chat_id", "")
    cfg = load_config()
    day = datetime.utcnow().date().isoformat()
    q = storage.get_queue(day)
    await message.answer(
        "Status\n"
        f"- Target: {target or '(not set)'}\n"
        f"- Items in DB: {storage.count_items()}\n"
        f"- Planned today: {len(q)} / {cfg.posts_per_day}\n"
    )


@router.message(Command("metrics"))
async def metrics_cmd(message: Message, storage: Storage):
    cfg = load_config()
    chat_id = storage.get_setting("target_chat_id", "").strip() or cfg.target_chat_id
    if not chat_id:
        await message.answer("Target chat id not set")
        return
    rows = storage.get_latest_metrics(chat_id=str(chat_id), limit=10)
    if not rows:
        await message.answer("No metrics yet. Run telethon collector.")
        return
    lines = ["Latest metrics:"]
    for r in rows[:10]:
        lines.append(
            f"- msg {r['message_id']}: views={r['views']} forwards={r['forwards']} replies={r['replies']} at {r['captured_at']}"
        )
    await message.answer("\n".join(lines))


@router.message(Command("postnow"))
async def postnow_cmd(message: Message, storage: Storage):
    target = storage.get_setting("target_chat_id", "") or str(message.chat.id)
    ok, info = await post_one(storage=storage, target_chat_id=target)
    await message.answer("Posted" if ok else f"Nothing posted: {info}")


@router.message(Command("plan"))
async def plan_cmd(message: Message, storage: Storage):
    cfg = load_config()
    ok, info = ensure_daily_queue(storage=storage, cfg=cfg)
    await message.answer(f"Planned: {ok}. {info}")
