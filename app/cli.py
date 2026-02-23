import argparse
from datetime import datetime

from .config import load_config
from .news import fetch_feeds
from .planner import ensure_daily_queue
from .storage import Storage


def main():
    p = argparse.ArgumentParser(prog="soarix-news-bot")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("fetch")
    sub.add_parser("plan")
    sub.add_parser("queue")

    args = p.parse_args()
    cfg = load_config()
    storage = Storage(cfg.db_path)

    if args.cmd == "fetch":
        n = fetch_feeds(storage)
        print(f"fetched={n} items_in_db={storage.count_items()}")
        return

    if args.cmd == "plan":
        ok, info = ensure_daily_queue(storage=storage, cfg=cfg)
        print(f"planned={ok} {info}")
        return

    if args.cmd == "queue":
        day = datetime.utcnow().date().isoformat()
        q = storage.get_queue(day)
        print(f"day={day} slots={len(q)}")
        for row in q:
            print(f"- {row['slot']} {row['status']} {row['format']} {row['guid']}")
        return


if __name__ == "__main__":
    main()
