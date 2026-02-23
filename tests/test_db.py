import tempfile
import unittest
from pathlib import Path

from app.db import Database


class TestDatabase(unittest.TestCase):
    def test_db_settings_and_seen(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "test.db")

            db.set_setting("target_chat_id", "123")
            self.assertEqual(db.get_setting("target_chat_id"), "123")

            self.assertFalse(db.is_seen("https://example.com"))
            db.mark_seen("https://example.com", "Title", "Source", "2026-01-01")
            self.assertTrue(db.is_seen("https://example.com"))
            self.assertTrue(db.is_seen_title_source("Title", "Source"))


if __name__ == "__main__":
    unittest.main()
