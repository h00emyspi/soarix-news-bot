from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from telethon import TelegramClient

from .config import load_config
from .storage import Storage


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _reactions_to_json(message) -> str:
    # message.reactions can be None
    try:
        r = message.reactions
        if not r or not getattr(r, "results", None):
            return "{}"
        out = {}
        for x in r.results:
            # x.reaction is a Reaction object; stringify best-effort
            key = str(getattr(x, "reaction", "reaction"))
            out[key] = int(getattr(x, "count", 0) or 0)
        return json.dumps(out, ensure_ascii=False)
    except Exception:
        return "{}"


async def collect_once(*, storage: Storage) -> tuple[bool, str]:
    cfg = load_config()
    if not cfg.telethon_api_id or not cfg.telethon_api_hash:
        return False, "TELETHON_API_ID/TELETHON_API_HASH missing"

    chat_id = storage.get_setting("target_chat_id", "").strip() or cfg.target_chat_id
    if not chat_id:
        return False, "target_chat_id not set"

    msg_ids = storage.list_recent_posted_message_ids(limit=200)

    client = TelegramClient(cfg.telethon_session, cfg.telethon_api_id, cfg.telethon_api_hash)
    await client.start()  # first run will ask for phone/code in console
    entity = await client.get_entity(chat_id)

    captured_at = _now_utc_iso()
    if msg_ids:
        msgs = await client.get_messages(entity, ids=msg_ids)
    else:
        # If there is no queue history yet (e.g. bot was just installed),
        # collect metrics for the most recent posts in the channel.
        msgs = await client.get_messages(entity, limit=max(5, int(cfg.metrics_recent_limit)))
    count = 0
    for m in msgs:
        if not m:
            continue
        # Skip service messages if any
        try:
            if getattr(m, "message", None) is None and getattr(m, "text", None) is None:
                continue
        except Exception:
            pass
        views = int(getattr(m, "views", 0) or 0)
        forwards = int(getattr(m, "forwards", 0) or 0)
        replies = 0
        try:
            if m.replies and getattr(m.replies, "replies", None) is not None:
                replies = int(m.replies.replies or 0)
        except Exception:
            replies = 0
        reactions_json = _reactions_to_json(m)

        storage.add_metric_snapshot(
            chat_id=str(chat_id),
            message_id=int(m.id),
            captured_at=captured_at,
            views=views,
            forwards=forwards,
            replies=replies,
            reactions_json=reactions_json,
        )
        count += 1

    await client.disconnect()
    if count == 0:
        return False, "no messages collected"
    mode = "by_queue" if msg_ids else "recent"
    return True, f"mode={mode} snapshots={count}"


async def run_loop(*, storage: Storage):
    cfg = load_config()
    while True:
        ok, info = await collect_once(storage=storage)
        print(f"collector: ok={ok} info={info}")
        await asyncio.sleep(max(60, int(cfg.collect_interval_seconds)))


def main():
    cfg = load_config()
    storage = Storage(cfg.db_path)
    asyncio.run(run_loop(storage=storage))


if __name__ == "__main__":
    main()
