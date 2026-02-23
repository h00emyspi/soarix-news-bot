from __future__ import annotations

import requests

from app.config import Config
from app.rss import NewsItem, compact_text


SYSTEM_PROMPT = (
    "Ты редактор телеграм-канала про AI/LLM/агентов. "
    "Перепиши новость в короткий пост на русском языке. "
    "Формат: 2-4 коротких абзаца + 3-5 хэштегов в конце. "
    "Факты не выдумывай, не добавляй то, чего нет в тексте."
)


class LLMRewriter:
    def __init__(self, config: Config):
        self.config = config

    def rewrite(self, item: NewsItem) -> str:
        user_prompt = (
            f"Заголовок: {item.title}\n"
            f"Источник: {item.source}\n"
            f"Ссылка: {item.link}\n"
            f"Текст: {compact_text(item.summary, 1800)}"
        )

        if self.config.openai_api_key:
            text = self._rewrite_openai(user_prompt)
            if text:
                return text

        text = self._rewrite_ollama(user_prompt)
        if text:
            return text

        return self._fallback(item)

    def _rewrite_openai(self, user_prompt: str) -> str | None:
        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.config.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.config.openai_model,
                    "temperature": 0.3,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                },
                timeout=35,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception:
            return None

    def _rewrite_ollama(self, user_prompt: str) -> str | None:
        try:
            response = requests.post(
                f"{self.config.ollama_base_url.rstrip('/')}/api/chat",
                json={
                    "model": self.config.ollama_model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    "stream": False,
                },
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "").strip() or None
        except Exception:
            return None

    def _fallback(self, item: NewsItem) -> str:
        return (
            f"📰 {item.title}\n\n"
            f"{compact_text(item.summary, 600)}\n\n"
            f"Источник: {item.source}\n"
            "#AI #LLM #Новости"
        )
