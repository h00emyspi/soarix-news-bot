from __future__ import annotations

import asyncio
import json
import threading
import urllib.parse
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .config import Config
from .publisher import post_one
from .storage import Storage


_POST_NOW_LOCK = threading.Lock()


def _render_html(cfg: Config, storage: Storage) -> str:
    metrics = storage.get_metrics_summary()
    recent = storage.get_recent_posts(30)
    target = storage.get_setting("target_chat_id", "")

    top_sources_rows = "".join(
        f"<tr><td>{escape(str(row['source']))}</td><td>{int(row['count'])}</td></tr>" for row in metrics["top_sources"]
    )
    recent_rows = "".join(
        "<tr>"
        f"<td>{escape(str(item.get('posted_at') or ''))}</td>"
        f"<td>{escape(str(item.get('source') or ''))}</td>"
        f"<td>{escape(str(item.get('title') or ''))}</td>"
        f"<td><a href='{escape(str(item.get('link') or ''))}' target='_blank' rel='noreferrer'>открыть</a></td>"
        "</tr>"
        for item in recent
    )

    post_times = ", ".join(cfg.post_times[: cfg.max_posts_per_day])

    return f"""<!doctype html>
<html>
<head>
  <meta charset='utf-8' />
  <title>SOARIX Панель управления</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; background: #fafafa; }}
    .grid {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom:20px; }}
    .card {{ background:#fff; border:1px solid #ddd; border-radius:10px; padding:16px; }}
    table {{ width:100%; border-collapse: collapse; background: #fff; margin-bottom: 20px; }}
    th, td {{ border:1px solid #ddd; padding:8px; text-align:left; font-size: 14px; }}
    form {{ display:flex; gap:8px; flex-wrap: wrap; margin-bottom:16px; }}
    input {{ padding:8px; min-width: 320px; }}
    button {{ padding:8px 12px; cursor:pointer; }}
  </style>
</head>
<body>
  <h1>SOARIX News Bot — панель управления</h1>
  <p>Метрики публикаций, target_chat_id и ручная публикация.</p>

  <div class='grid'>
    <div class='card'><b>Всего публикаций</b><br/>{metrics['total_posts']}</div>
    <div class='card'><b>Публикаций за 24 часа</b><br/>{metrics['posts_last_24h']}</div>
    <div class='card'><b>Часовой пояс</b><br/>{escape(cfg.timezone)}</div>
    <div class='card'><b>Время публикаций</b><br/>{escape(post_times)}</div>
  </div>

  <h3>Управление</h3>
  <form method='post' action='/set-target'>
    <input name='target_chat_id' placeholder='target_chat_id (e.g. -100...)' value='{escape(target)}' />
    <button type='submit'>Сохранить target_chat_id</button>
  </form>
  <form method='post' action='/post-now'>
    <button type='submit'>Опубликовать сейчас</button>
  </form>

  <h3>Топ источников</h3>
  <table>
    <thead><tr><th>Источник</th><th>Количество</th></tr></thead>
    <tbody>{top_sources_rows}</tbody>
  </table>

  <h3>Последние публикации</h3>
  <table>
    <thead><tr><th>Время</th><th>Источник</th><th>Заголовок</th><th>Ссылка</th></tr></thead>
    <tbody>{recent_rows}</tbody>
  </table>
</body>
</html>
"""


def create_dashboard_server(*, cfg: Config, storage: Storage, host: str, port: int) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def _send_json(self, payload: dict, status: int = 200):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_html(self, html: str):
            body = html.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):  # noqa: N802
            if self.path == "/":
                self._send_html(_render_html(cfg, storage))
                return
            if self.path == "/health":
                self._send_json({"status": "ok"})
                return
            if self.path == "/api/metrics":
                self._send_json(storage.get_metrics_summary())
                return

            self._send_json({"error": "not found"}, status=404)

        def do_POST(self):  # noqa: N802
            content_length = int(self.headers.get("Content-Length", "0"))
            raw_data = self.rfile.read(content_length).decode("utf-8") if content_length else ""
            form_data = urllib.parse.parse_qs(raw_data)

            if self.path == "/set-target":
                target = (form_data.get("target_chat_id", [""])[0] or "").strip()
                if target:
                    storage.set_setting("target_chat_id", target)
                self.send_response(HTTPStatus.FOUND)
                self.send_header("Location", "/")
                self.end_headers()
                return

            if self.path == "/post-now":
                if not _POST_NOW_LOCK.acquire(blocking=False):
                    self._send_json({"ok": False, "error": "publish already in progress"}, status=409)
                    return
                try:
                    target = storage.get_setting("target_chat_id", "") or cfg.target_chat_id
                    if not target:
                        self._send_json({"ok": False, "error": "target_chat_id not set"}, status=400)
                        return

                    ok, info = asyncio.run(post_one(storage=storage, target_chat_id=str(target)))
                    self._send_json({"ok": ok, "info": info})
                finally:
                    _POST_NOW_LOCK.release()
                return

            self._send_json({"error": "not found"}, status=404)

        def log_message(self, format: str, *args):  # noqa: A003
            return

    return ThreadingHTTPServer((host, port), Handler)


def run_dashboard(cfg: Config, *, host: str = "0.0.0.0", port: int | None = None):
    storage = Storage(cfg.db_path)
    if cfg.target_chat_id:
        storage.set_setting("target_chat_id", cfg.target_chat_id)

    p = int(port if port is not None else cfg.dashboard_port)
    server = create_dashboard_server(cfg=cfg, storage=storage, host=host, port=p)
    try:
        server.serve_forever()
    finally:
        server.server_close()
