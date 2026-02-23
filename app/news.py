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


def score_item(*, title: str, summary: str, source: str) -> int:
    """Cheap heuristic score for 'top topics'."""
    text = (title or "") + " " + (summary or "")
    t = text.lower()
    score = 0

    # Keyword hits
    for k in KEYWORDS:
        if k.lower() in t:
            score += 2

    # Topic boosters
    boosters = {
        "agent": 6,
        "multi-agent": 6,
        "mcp": 6,
        "tool": 3,
        "function calling": 4,
        "release": 3,
        "launch": 3,
        "paper": 3,
        "arxiv": 3,
        "benchmark": 3,
        "security": 2,
        "openai": 2,
        "anthropic": 2,
        "gemini": 2,
        "deepmind": 2,
    }
    for k, v in boosters.items():
        if k in t:
            score += v

    # Source weights
    source_w = {
        "OpenAI": 4,
        "DeepMind": 3,
        "Google AI": 3,
        "Hugging Face": 3,
        "Anthropic": 3,
    }.get(source or "", 0)
    score += source_w

    # Keep within a sane range
    if score < 0:
        score = 0
    if score > 200:
        score = 200
    return score


def bucket_topic(*, title: str, summary: str) -> str:
    t = ((title or "") + " " + (summary or "")).lower()
    if "mcp" in t or "tool" in t or "function calling" in t or "sdk" in t:
        return "tools"
    if "agent" in t or "multi-agent" in t or "агент" in t:
        return "agents"
    if "release" in t or "launch" in t or "update" in t:
        return "releases"
    if "paper" in t or "arxiv" in t or "benchmark" in t:
        return "research"
    if "security" in t or "safety" in t or "alignment" in t:
        return "safety"
    return "general"
