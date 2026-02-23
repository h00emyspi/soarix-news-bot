import json
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from app.config import Config
from app.dashboard import run_dashboard
from app.db import Database


class TestDashboard(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.tmp.name) / "test.db"
        cls.config = Config(
            telegram_bot_token="123:test",
            db_path=cls.db_path,
            post_times=["09:00"],
            rss_feeds=["https://example.com/rss"],
            max_posts_per_day=1,
            timezone="UTC",
            ollama_base_url="http://localhost:11434",
            ollama_model="llama3.1:8b",
            openai_api_key="",
            openai_model="gpt-4o-mini",
        )
        cls.port = 18080
        cls.thread = threading.Thread(
            target=run_dashboard,
            kwargs={"config": cls.config, "host": "127.0.0.1", "port": cls.port},
            daemon=True,
        )
        cls.thread.start()
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def test_health_and_metrics(self) -> None:
        health = urllib.request.urlopen(f"http://127.0.0.1:{self.port}/health", timeout=3)
        self.assertEqual(health.status, 200)
        payload = json.loads(health.read().decode("utf-8"))
        self.assertEqual(payload["status"], "ok")

        metrics = urllib.request.urlopen(f"http://127.0.0.1:{self.port}/api/metrics", timeout=3)
        self.assertEqual(metrics.status, 200)
        data = json.loads(metrics.read().decode("utf-8"))
        self.assertIn("total_posts", data)

    def test_set_target(self) -> None:
        encoded = urllib.parse.urlencode({"target_chat_id": "777"}).encode("utf-8")
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/set-target",
            data=encoded,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            self.assertIn(resp.status, (200, 302))

        db = Database(self.db_path)
        self.assertEqual(db.get_setting("target_chat_id"), "777")


if __name__ == "__main__":
    unittest.main()
