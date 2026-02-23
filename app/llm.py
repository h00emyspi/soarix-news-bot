import json
import re
import requests


def _strip(s: str) -> str:
    return (s or "").strip()


class LLM:
    def __init__(self, *, ollama_base_url: str, ollama_model: str, openai_api_key: str, openai_model: str):
        self.ollama_base_url = _strip(ollama_base_url).rstrip("/")
        self.ollama_model = _strip(ollama_model)
        self.openai_api_key = _strip(openai_api_key)
        self.openai_model = _strip(openai_model) or "gpt-3.5-turbo"

    def rewrite_news(self, *, title: str, source: str, link: str, summary: str, lang: str = "ru") -> str:
        sys = (
            "Ты редактор Telegram-канала про AI (агенты, LLM, автоматизация). "
            "Перепиши новость в виде короткого поста."
        )
        user = f"""Источник: {source}
Заголовок: {title}
Ссылка: {link}
Текст/анонс:
{summary}

Сделай пост на языке: {lang}.
Требования:
- 1 строка: сильный заголовок
- 3-5 буллетов с фактами/выводами
- 1 практический takeaway
- В конце: ссылка
- 2-5 хэштегов
- Не выдумывай факты. Если данных мало - так и скажи.
"""

        # Prefer Ollama
        ollama = self._ollama_generate(system=sys, prompt=user)
        if ollama:
            return ollama

        # Fallback OpenAI
        openai = self._openai_chat(system=sys, user=user)
        if openai:
            return openai

        return f"{title}\n\n- (нет LLM ответа)\n\n{link}\n#ai"

    def _ollama_generate(self, *, system: str, prompt: str) -> str | None:
        if not self.ollama_base_url or not self.ollama_model:
            return None
        try:
            payload = {"model": self.ollama_model, "prompt": f"{system}\n\n{prompt}", "stream": False}
            r = requests.post(f"{self.ollama_base_url}/api/generate", json=payload, timeout=60)
            if r.status_code != 200:
                return None
            data = r.json()
            return _strip(data.get("response", "")) or None
        except Exception:
            return None

    def _openai_chat(self, *, system: str, user: str) -> str | None:
        if not self.openai_api_key:
            return None
        try:
            headers = {"Authorization": f"Bearer {self.openai_api_key}", "Content-Type": "application/json"}
            payload = {
                "model": self.openai_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.5,
                "max_tokens": 650,
            }
            r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=60)
            if r.status_code != 200:
                return None
            data = r.json()
            return _strip(data["choices"][0]["message"]["content"]) or None
        except Exception:
            return None
