from __future__ import annotations

from datetime import datetime, timezone
import time

from .agents import OrchestratorAgent, WriterAgent, CriticAgent, ReviserAgent
from .config import Config
from .llm import LLM
from .news import fetch_feeds, score_item, bucket_topic
from .storage import Storage


def _today_utc() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def ensure_daily_queue(*, storage: Storage, cfg: Config) -> tuple[bool, str]:
    day = _today_utc()
    existing = storage.get_queue(day)
    if len(existing) >= cfg.posts_per_day:
        return False, "queue already planned"

    added = fetch_feeds(storage)

    # Slots come from config times
    slots = cfg.post_times[: cfg.posts_per_day]

    llm = LLM(
        ollama_base_url=cfg.ollama_base_url,
        ollama_model=cfg.ollama_model,
        openai_api_key=cfg.openai_api_key,
        openai_model=cfg.openai_model,
        timeout_seconds=cfg.llm_timeout_seconds,
        prefer_ollama=cfg.prefer_ollama,
    )
    orchestrator = OrchestratorAgent(llm)
    writer = WriterAgent(llm)
    critic = CriticAgent(llm)
    reviser = ReviserAgent(llm)

    formats = orchestrator.pick_formats(slots)

    # Select top items with diversity by bucket + source.
    planned = 0
    exclude = {q["guid"] for q in existing if q.get("guid")}

    candidates = [c for c in storage.list_unposted(limit=300) if c.get("guid") not in exclude]
    ranked = []
    for c in candidates:
        s = score_item(title=c.get("title", ""), summary=c.get("summary", ""), source=c.get("source", ""))
        b = bucket_topic(title=c.get("title", ""), summary=c.get("summary", ""))
        ranked.append((s, b, c))
    ranked.sort(key=lambda x: x[0], reverse=True)

    used_buckets: set[str] = set()
    used_sources: set[str] = set()

    def pick_next(prefer_bucket: str | None):
        for s, b, c in ranked:
            if c["guid"] in exclude:
                continue
            if prefer_bucket and b != prefer_bucket:
                continue
            if c.get("source") in used_sources:
                continue
            return s, b, c
        for s, b, c in ranked:
            if c["guid"] in exclude:
                continue
            if c.get("source") in used_sources:
                continue
            return s, b, c
        for s, b, c in ranked:
            if c["guid"] in exclude:
                continue
            return s, b, c
        return None

    slot_bucket = {
        slots[0] if len(slots) > 0 else "": "agents",
        slots[1] if len(slots) > 1 else "": "tools",
        slots[2] if len(slots) > 2 else "": "releases",
        slots[3] if len(slots) > 3 else "": "research",
        slots[4] if len(slots) > 4 else "": "safety",
        slots[5] if len(slots) > 5 else "": "general",
    }

    for slot in slots:
        if storage.get_queue_slot(day, slot):
            continue
        pref = slot_bucket.get(slot)
        picked = pick_next(pref)
        if not picked:
            break
        _, b, item = picked
        exclude.add(item["guid"])
        used_buckets.add(b)
        if item.get("source"):
            used_sources.add(item["source"])
        p = writer.write(
            title=item["title"],
            source=item["source"],
            link=item["link"],
            summary=item["summary"],
            format=formats.get(slot, "breaking_news"),
            lang=cfg.lang,
        )

        improved = p.post_text
        if cfg.enable_review:
            t0 = time.time()
            critique = critic.review(post_text=improved, lang=cfg.lang)
            improved = reviser.revise(post_text=improved, critique=critique, lang=cfg.lang)
            # If review cycle is too slow, disable it for this run.
            if (time.time() - t0) > max(6, cfg.llm_timeout_seconds):
                cfg.enable_review = False
        storage.upsert_queue_slot(
            day=day,
            slot=slot,
            guid=item["guid"],
            format=formats.get(slot, "breaking_news"),
            alt_title_1=p.alt_title_1,
            alt_title_2=p.alt_title_2,
            post_text=improved,
        )
        planned += 1

    return True, f"feeds_added={added}, planned={planned}"
