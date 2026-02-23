import json
import tempfile
import threading
import time
import unittest
import urllib.parse
import urllib.request

from app.config import Config
from app.dashboard import create_dashboard_server
from app.storage import Storage


class TestDashboard(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db_path = cls.tmp.name + "/test.db"
        cls.storage = Storage(cls.db_path)
        cls.cfg = Config(
            telegram_bot_token="123:test",
            app_mode="dashboard",
            dashboard_port=18080,
            timezone="UTC",
            target_chat_id="",
            post_times=["09:00"],
            max_posts_per_day=1,
            rss_feeds=["https://example.com/rss"],
            lang="ru",
            db_path=cls.db_path,
            ollama_base_url="http://localhost:11434",
            ollama_model="llama3.1:8b",
            openai_api_key="",
            openai_model="gpt-3.5-turbo",
            llm_timeout_seconds=5,
            prefer_ollama=True,
            enable_review=False,
            telethon_api_id=0,
            telethon_api_hash="",
            telethon_session="test",
            collect_interval_seconds=600,
            metrics_recent_limit=10,
        )
        cls.server = create_dashboard_server(cfg=cls.cfg, storage=cls.storage, host="127.0.0.1", port=18080)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.2)

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            cls.server.shutdown()
            cls.server.server_close()
        finally:
            cls.tmp.cleanup()

    def test_health_and_metrics(self) -> None:
        with urllib.request.urlopen("http://127.0.0.1:18080/health", timeout=3) as resp:
            self.assertEqual(resp.status, 200)
            payload = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(payload["status"], "ok")

        with urllib.request.urlopen("http://127.0.0.1:18080/api/metrics", timeout=3) as resp:
            self.assertEqual(resp.status, 200)
            payload = json.loads(resp.read().decode("utf-8"))
            self.assertIn("total_posts", payload)

    def test_set_target_redirect(self) -> None:
        encoded = urllib.parse.urlencode({"target_chat_id": "777"}).encode("utf-8")
        req = urllib.request.Request(
            "http://127.0.0.1:18080/set-target",
            data=encoded,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            self.assertIn(resp.status, (200, 302))

        self.assertEqual(self.storage.get_setting("target_chat_id", ""), "777")


if __name__ == "__main__":
    unittest.main()
