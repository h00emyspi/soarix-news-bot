import sqlite3
from datetime import datetime


SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  guid TEXT UNIQUE,
  source TEXT,
  title TEXT,
  link TEXT,
  published TEXT,
  summary TEXT,
  selected INTEGER DEFAULT 0,
  rewritten TEXT,
  posted_at TEXT
);

CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT
);
"""


class Storage:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _init(self):
        con = self._conn()
        cur = con.cursor()
        cur.executescript(SCHEMA)
        con.commit()
        con.close()

    def upsert_item(self, guid: str, source: str, title: str, link: str, published: str, summary: str):
        con = self._conn()
        cur = con.cursor()
        cur.execute(
            """
            INSERT OR IGNORE INTO items (guid, source, title, link, published, summary)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (guid, source, title, link, published, summary),
        )
        con.commit()
        con.close()

    def pick_next_unposted(self):
        con = self._conn()
        cur = con.cursor()
        cur.execute(
            """
            SELECT guid, source, title, link, published, summary
            FROM items
            WHERE posted_at IS NULL
            ORDER BY COALESCE(published, '') DESC, id DESC
            LIMIT 1
            """
        )
        row = cur.fetchone()
        con.close()
        if not row:
            return None
        return {
            "guid": row[0],
            "source": row[1],
            "title": row[2],
            "link": row[3],
            "published": row[4],
            "summary": row[5],
        }

    def mark_posted(self, guid: str, rewritten: str):
        con = self._conn()
        cur = con.cursor()
        cur.execute(
            "UPDATE items SET rewritten=?, posted_at=? WHERE guid=?",
            (rewritten, datetime.utcnow().isoformat(), guid),
        )
        con.commit()
        con.close()

    def set_setting(self, key: str, value: str):
        con = self._conn()
        cur = con.cursor()
        cur.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        con.commit()
        con.close()

    def get_setting(self, key: str, default: str = "") -> str:
        con = self._conn()
        cur = con.cursor()
        cur.execute("SELECT value FROM settings WHERE key=?", (key,))
        row = cur.fetchone()
        con.close()
        return row[0] if row else default
