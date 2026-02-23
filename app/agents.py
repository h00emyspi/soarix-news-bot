from __future__ import annotations

import json
import re
from dataclasses import dataclass

from .llm import LLM


def _extract_json_obj(text: str) -> dict | None:
    if not text:
        return None
    s = text.strip()
    start = s.find("{")
    end = s.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(s[start : end + 1])
    except Exception:
        return None


def _clamp(s: str, n: int) -> str:
    s = (s or "").strip()
    if len(s) <= n:
        return s
    return s[:n].rstrip() + "…"


@dataclass
class PlannedPost:
    guid: str
    format: str
    alt_title_1: str
    alt_title_2: str
    post_text: str


class OrchestratorAgent:
    def __init__(self, llm: LLM):
        self.llm = llm

    def pick_formats(self, slots: list[str]) -> dict[str, str]:
        # Deterministic rubric by time (works well for channels)
        formats = [
            "breaking_news",
            "tool_of_the_day",
            "explain_like_5",
            "opinionated_take",
            "use_case",
            "daily_digest",
        ]
        out: dict[str, str] = {}
        for i, slot in enumerate(slots):
            out[slot] = formats[i % len(formats)]
        return out


class WriterAgent:
    def __init__(self, llm: LLM):
        self.llm = llm

    def write(self, *, title: str, source: str, link: str, summary: str, format: str, lang: str) -> PlannedPost:
        sys = "Ты редактор Telegram-канала про AI/LLM/AI-агентов. Пиши четко, кратко, без воды."
        style_map = {
            "breaking_news": "Срочная новость: коротко, что случилось и почему важно.",
            "tool_of_the_day": "Сфокусируйся на практическом инструменте/фиче и как применить.",
            "explain_like_5": "Объясни простыми словами, но без потери смысла.",
            "opinionated_take": "Дай осторожное мнение + аргументы + риски.",
            "use_case": "Опиши кейс применения: проблема→решение→результат.",
            "daily_digest": "Дай сжатый дайджест 1 новости с выводами.",
        }
        style = style_map.get(format, "Новостной пост")

        user = f"""Дано:
- Источник: {source}
- Заголовок: {title}
- Ссылка: {link}
- Анонс/текст:
{summary}

Сделай пост на языке: {lang}.
Стиль: {style}

Верни строго JSON:
{{
  "alt_title_1": "...",
  "alt_title_2": "...",
  "post": "..." 
}}

Правила:
- post <= 900 символов
- 1 строка заголовок, затем 3-6 буллетов, затем 1 takeaway, затем ссылка, затем 2-5 хэштегов
- Не выдумывай факты. Если данных мало - явно отметь.
"""

        raw = None
        if self.llm.prefer_ollama:
            raw = self.llm._ollama_generate(system=sys, prompt=user)
            if not raw:
                raw = self.llm._openai_chat(system=sys, user=user)
        else:
            raw = self.llm._openai_chat(system=sys, user=user)
            if not raw:
                raw = self.llm._ollama_generate(system=sys, prompt=user)

        obj = _extract_json_obj(raw or "")
        if not obj:
            # fallback to existing freeform rewrite
            text = self.llm.rewrite_news(title=title, source=source, link=link, summary=summary, lang=lang)
            return PlannedPost(guid=link or title, format=format, alt_title_1=title, alt_title_2=title, post_text=text)

        alt1 = _clamp(str(obj.get("alt_title_1", "")), 90) or _clamp(title, 90)
        alt2 = _clamp(str(obj.get("alt_title_2", "")), 90) or alt1
        post = (obj.get("post") or "").strip()
        if not post:
            post = self.llm.rewrite_news(title=title, source=source, link=link, summary=summary, lang=lang)
        return PlannedPost(guid=link or title, format=format, alt_title_1=alt1, alt_title_2=alt2, post_text=post)


class CriticAgent:
    def __init__(self, llm: LLM):
        self.llm = llm

    def review(self, *, post_text: str, lang: str) -> str:
        sys = "Ты строгий редактор-критик Telegram-постов."
        user = f"""Проверь пост (язык: {lang}).

Пост:
{post_text}

Верни 5-10 пунктов:
- фактические риски/галлюцинации
- что неясно/слишком длинно
- что улучшить в первом экране
"""
        out = None
        if self.llm.prefer_ollama:
            out = self.llm._ollama_generate(system=sys, prompt=user)
            if not out:
                out = self.llm._openai_chat(system=sys, user=user)
        else:
            out = self.llm._openai_chat(system=sys, user=user)
            if not out:
                out = self.llm._ollama_generate(system=sys, prompt=user)
        return (out or "").strip()


class ReviserAgent:
    def __init__(self, llm: LLM):
        self.llm = llm

    def revise(self, *, post_text: str, critique: str, lang: str) -> str:
        sys = "Ты редактор. Улучши пост по замечаниям критика."
        user = f"""Язык: {lang}

Исходный пост:
{post_text}

Замечания критика:
{critique}

Сделай улучшенную версию. Ограничения:
- <= 900 символов
- заголовок + 3-6 буллетов + takeaway + ссылка + 2-5 хэштегов
- не добавляй новых фактов, которых не было
"""
        out = None
        if self.llm.prefer_ollama:
            out = self.llm._ollama_generate(system=sys, prompt=user)
            if not out:
                out = self.llm._openai_chat(system=sys, user=user)
        else:
            out = self.llm._openai_chat(system=sys, user=user)
            if not out:
                out = self.llm._ollama_generate(system=sys, prompt=user)
        return (out or post_text).strip()
