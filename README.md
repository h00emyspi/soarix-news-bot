# SOARIX News Bot

Бот для Telegram, который:
- забирает новости из RSS-лент (AI/agents/LLM-тематика);
- переписывает их в короткие посты на русском через LLM (Ollama или OpenAI);
- планирует до 6 публикаций в день;
- хранит состояние в SQLite, чтобы не публиковать дубликаты;
- предоставляет лёгкую веб-панель с метриками и управлением.

## Быстрый старт

1. Создайте и заполните `.env`:

```bash
cp .env.example .env
```

2. Установите зависимости:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Запустите приложение:

```bash
python -m app
```

## Режимы запуска

- Бот: `APP_MODE=bot`
- Панель управления: `APP_MODE=dashboard` (по умолчанию `http://localhost:8080`)
- Сборщик метрик Telethon: `APP_MODE=collector`

Упрощённый запуск (Linux/macOS):

```bash
bash scripts/run.sh
bash scripts/run.sh dashboard
bash scripts/run.sh collector
```

CLI-команды (опционально):

```bash
python -m app.cli fetch
python -m app.cli plan
python -m app.cli queue
```

## Настройка бота

1. Откройте диалог с ботом и отправьте `/start`.
2. Установите цель публикации:
   - в группе/канале: отправьте `/settarget`;
   - в личном чате: `/settarget @your_channel` или `/settarget -100123...`.
3. Сформируйте очередь на день (опционально): `/plan`.
4. Моментальная публикация (опционально): `/postnow`.
5. Проверка метрик: `/metrics`.

## Сбор метрик через Telethon

Telegram Bot API не отдаёт полную постовую аналитику каналов.
Для сбора просмотров/пересылок/реакций используйте MTProto-сборщик на Telethon
(авторизация происходит через ваш пользовательский Telegram-аккаунт).

1. Создайте API-данные на https://my.telegram.org.
2. Добавьте в `.env`:
   - `TELETHON_API_ID`
   - `TELETHON_API_HASH`
   - `TELETHON_SESSION`
3. Запустите сборщик:

```bash
python -m app.telethon_collector
```

## Основные переменные окружения

- `TELEGRAM_BOT_TOKEN`
- `APP_MODE` (`bot|dashboard|collector`)
- `DASHBOARD_PORT` (по умолчанию: `8080`)
- `TIMEZONE` (по умолчанию: `UTC`)
- `POST_TIMES` (по умолчанию: `09:00,12:00,15:00,18:00,21:00,00:00`)
- `MAX_POSTS_PER_DAY` (1..6)
- `RSS_FEEDS` (список RSS через запятую)

LLM-настройки:
- Ollama: `OLLAMA_BASE_URL`, `OLLAMA_MODEL`
- OpenAI: `OPENAI_API_KEY`, `OPENAI_MODEL`

## Панель управления

Эндпоинты:
- `GET /health`
- `GET /api/metrics`
- `POST /set-target`
- `POST /post-now`

## Проверки и CI

GitHub Actions (`.github/workflows/ci.yml`) запускает:
- `python -m compileall app`
- `python -m unittest discover -s tests -v`

## Примечания

- Используются только RSS-источники (без тяжёлого скрейпинга).
- Не коммитьте `.env` в репозиторий.
