from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from .publisher import post_one
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
    storage.set_setting("target_chat_id", str(message.chat.id))
    await message.answer(f"OK. TARGET_CHAT_ID = {message.chat.id}")


@router.message(Command("status"))
async def status_cmd(message: Message, storage: Storage):
    target = storage.get_setting("target_chat_id", "")
    await message.answer(f"Target chat id: {target or '(not set)'}")


@router.message(Command("postnow"))
async def postnow_cmd(message: Message, storage: Storage):
    target = storage.get_setting("target_chat_id", "") or str(message.chat.id)
    ok, info = await post_one(storage=storage, target_chat_id=target)
    await message.answer("Posted" if ok else f"Nothing posted: {info}")
