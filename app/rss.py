from __future__ import annotations

import calendar
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import feedparser

TRACKING_QUERY_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "utm_id",
    "gclid",
    "fbclid",
}


@dataclass
class NewsItem:
    title: str
    link: str
    summary: str
    source: str
    published: str
    published_ts: int


def canonicalize_link(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw)
    query_pairs = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if k.lower() not in TRACKING_QUERY_PARAMS]
    clean_query = urlencode(query_pairs)
    clean_path = parsed.path.rstrip("/") or parsed.path or "/"
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), clean_path, "", clean_query, ""))


def _entry_timestamp(entry: dict) -> int:
    for key in ("published_parsed", "updated_parsed"):
        value = entry.get(key)
        if value:
            return int(calendar.timegm(value))
    return 0


def fetch_news(feeds: list[str], limit_per_feed: int = 15) -> list[NewsItem]:
    items: list[NewsItem] = []

    for feed_url in feeds:
        parsed = feedparser.parse(feed_url)
        source = parsed.feed.get("title", feed_url)

        for entry in parsed.entries[:limit_per_feed]:
            title = str(entry.get("title", "")).strip()
            link = canonicalize_link(str(entry.get("link", "")).strip())
            if not title or not link:
                continue

            published = str(entry.get("published", "")).strip()
            summary = str(entry.get("summary", "")).strip()
            published_ts = _entry_timestamp(entry)

            items.append(
                NewsItem(
                    title=title,
                    link=link,
                    summary=summary,
                    source=source,
                    published=published,
                    published_ts=published_ts,
                )
            )

    items.sort(key=lambda item: (item.published_ts, item.published), reverse=True)
    return items


def compact_text(value: str, max_len: int = 1000) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= max_len:
        return normalized
    return normalized[: max_len - 1].rstrip() + "…"
