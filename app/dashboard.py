from __future__ import annotations

import asyncio
import json
import urllib.parse
import threading
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from app.bot import NewsBotApp
from app.config import Config, load_config
from app.db import Database


_POST_NOW_LOCK = threading.Lock()


def _render_html(config: Config, db: Database) -> str:
    metrics = db.get_metrics()
    recent = db.get_recent_items(30)
    target_chat_id = db.get_setting("target_chat_id") or ""

    top_sources_rows = "".join(
        f"<tr><td>{escape(str(row['source']))}</td><td>{int(row['count'])}</td></tr>" for row in metrics["top_sources"]
    )
    recent_rows = "".join(
        "<tr>"
        f"<td>{escape(str(item['created_at']))}</td>"
        f"<td>{escape(str(item['source'] or ''))}</td>"
        f"<td>{escape(str(item['title'] or ''))}</td>"
        f"<td><a href='{escape(str(item['link']))}' target='_blank' rel='noreferrer'>open</a></td>"
        "</tr>"
        for item in recent
    )

    return f"""
<!doctype html>
<html>
<head>
  <meta charset='utf-8' />
  <title>SOARIX Dashboard</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; background: #fafafa; }}
    .grid {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom:20px; }}
    .card {{ background:#fff; border:1px solid #ddd; border-radius:10px; padding:16px; }}
    table {{ width:100%; border-collapse: collapse; background: #fff; margin-bottom: 20px; }}
    th, td {{ border:1px solid #ddd; padding:8px; text-align:left; font-size: 14px; }}
    form {{ display:flex; gap:8px; flex-wrap: wrap; margin-bottom:16px; }}
    input {{ padding:8px; }}
    button {{ padding:8px 12px; cursor:pointer; }}
  </style>
</head>
<body>
  <h1>SOARIX News Bot Dashboard</h1>
  <p>Управление ботом, метрики публикаций и последние новости из БД.</p>

  <div class='grid'>
    <div class='card'><b>Total posts</b><br/>{metrics['total_posts']}</div>
    <div class='card'><b>Posts last 24h</b><br/>{metrics['posts_last_24h']}</div>
    <div class='card'><b>Timezone</b><br/>{escape(config.timezone)}</div>
    <div class='card'><b>Post times</b><br/>{escape(', '.join(config.post_times[:config.max_posts_per_day]))}</div>
  </div>

  <h3>Управление</h3>
  <form method='post' action='/set-target'>
    <input name='target_chat_id' placeholder='target_chat_id' value='{escape(target_chat_id)}' />
    <button type='submit'>Сохранить target_chat_id</button>
  </form>
  <form method='post' action='/post-now'>
    <button type='submit'>Опубликовать сейчас</button>
  </form>

  <h3>Top sources</h3>
  <table>
    <thead><tr><th>Source</th><th>Count</th></tr></thead>
    <tbody>{top_sources_rows}</tbody>
  </table>

  <h3>Recent posts</h3>
  <table>
    <thead><tr><th>Created</th><th>Source</th><th>Title</th><th>Link</th></tr></thead>
    <tbody>{recent_rows}</tbody>
  </table>
</body>
</html>
"""


def run_dashboard(config: Config | None = None, host: str = "0.0.0.0", port: int = 8080) -> None:
    cfg = config or load_config()
    db = Database(cfg.db_path)

    class Handler(BaseHTTPRequestHandler):
        def _send_json(self, payload: dict[str, object], status: int = 200) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_html(self, html: str) -> None:
            body = html.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/":
                self._send_html(_render_html(cfg, db))
                return
            if self.path == "/health":
                self._send_json({"status": "ok"})
                return
            if self.path == "/api/metrics":
                self._send_json(db.get_metrics())
                return

            self._send_json({"error": "not found"}, status=404)

        def do_POST(self) -> None:  # noqa: N802
            content_length = int(self.headers.get("Content-Length", "0"))
            raw_data = self.rfile.read(content_length).decode("utf-8") if content_length else ""
            form_data = urllib.parse.parse_qs(raw_data)

            if self.path == "/set-target":
                target = (form_data.get("target_chat_id", [""])[0] or "").strip()
                if target:
                    db.set_setting("target_chat_id", target)
                self.send_response(HTTPStatus.FOUND)
                self.send_header("Location", "/")
                self.end_headers()
                return

            if self.path == "/post-now":
                if not _POST_NOW_LOCK.acquire(blocking=False):
                    self._send_json({"ok": False, "error": "publish already in progress"}, status=409)
                    return
                try:
                    async def _post_once() -> bool:
                        bot = NewsBotApp(cfg)
                        try:
                            return await bot.publish_one_news()
                        finally:
                            await bot.bot.session.close()

                    ok = asyncio.run(_post_once())
                    self._send_json({"ok": ok})
                finally:
                    _POST_NOW_LOCK.release()
                return

            self._send_json({"error": "not found"}, status=404)

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

    server = ThreadingHTTPServer((host, port), Handler)
    try:
        server.serve_forever()
    finally:
        server.server_close()


def main() -> None:
    cfg = load_config()
    run_dashboard(cfg)


if __name__ == "__main__":
    main()
