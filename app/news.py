from __future__ import annotations

import time
from datetime import datetime
import feedparser

from .feeds import FEEDS, KEYWORDS
from .storage import Storage


def _contains_keywords(text: str) -> bool:
    t = (text or "").lower()
    return any(k.lower() in t for k in KEYWORDS)


def fetch_feeds(storage: Storage) -> int:
    added = 0
    for source, url in FEEDS:
        feed = feedparser.parse(url)
        for e in feed.entries[:20]:
            title = getattr(e, "title", "") or ""
            summary = getattr(e, "summary", "") or getattr(e, "description", "") or ""
            link = getattr(e, "link", "") or ""
            guid = getattr(e, "id", "") or link or (source + title)
            published = getattr(e, "published", "") or ""
            if not _contains_keywords(title + " " + summary):
                continue
            storage.upsert_item(guid=guid, source=source, title=title, link=link, published=published, summary=summary)
            added += 1
        time.sleep(0.2)
    return added
