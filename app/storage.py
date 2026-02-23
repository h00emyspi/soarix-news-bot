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

CREATE TABLE IF NOT EXISTS queue (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  day TEXT,
  slot TEXT,
  guid TEXT,
  format TEXT,
  alt_title_1 TEXT,
  alt_title_2 TEXT,
  post_text TEXT,
  status TEXT DEFAULT 'planned',
  tg_message_id INTEGER,
  error TEXT,
  created_at TEXT,
  posted_at TEXT,
  UNIQUE(day, slot)
);

CREATE TABLE IF NOT EXISTS metrics (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  captured_at TEXT,
  chat_id TEXT,
  message_id INTEGER,
  views INTEGER,
  forwards INTEGER,
  replies INTEGER,
  reactions_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_metrics_msg ON metrics(chat_id, message_id, captured_at);

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

    def list_unposted(self, limit: int = 200):
        con = self._conn()
        cur = con.cursor()
        cur.execute(
            """
            SELECT guid, source, title, link, published, summary
            FROM items
            WHERE posted_at IS NULL
            ORDER BY COALESCE(published, '') DESC, id DESC
            LIMIT ?
            """,
            (int(limit),),
        )
        rows = cur.fetchall()
        con.close()
        return [
            {
                "guid": r[0],
                "source": r[1],
                "title": r[2],
                "link": r[3],
                "published": r[4],
                "summary": r[5],
            }
            for r in rows
        ]

    def pick_next_unposted_excluding(self, exclude_guids: set[str]):
        exclude = list(exclude_guids or set())
        con = self._conn()
        cur = con.cursor()

        if exclude:
            placeholders = ",".join(["?"] * len(exclude))
            cur.execute(
                f"""
                SELECT guid, source, title, link, published, summary
                FROM items
                WHERE posted_at IS NULL AND guid NOT IN ({placeholders})
                ORDER BY COALESCE(published, '') DESC, id DESC
                LIMIT 1
                """,
                tuple(exclude),
            )
        else:
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

    def get_item(self, guid: str):
        con = self._conn()
        cur = con.cursor()
        cur.execute(
            "SELECT guid, source, title, link, published, summary, posted_at FROM items WHERE guid=?",
            (guid,),
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
            "posted_at": row[6],
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

    def get_queue(self, day: str):
        con = self._conn()
        cur = con.cursor()
        cur.execute(
            "SELECT day, slot, guid, format, status, tg_message_id, error FROM queue WHERE day=? ORDER BY slot",
            (day,),
        )
        rows = cur.fetchall()
        con.close()
        return [
            {
                "day": r[0],
                "slot": r[1],
                "guid": r[2],
                "format": r[3],
                "status": r[4],
                "tg_message_id": r[5],
                "error": r[6],
            }
            for r in rows
        ]

    def upsert_queue_slot(
        self,
        *,
        day: str,
        slot: str,
        guid: str,
        format: str,
        alt_title_1: str,
        alt_title_2: str,
        post_text: str,
    ):
        con = self._conn()
        cur = con.cursor()
        cur.execute(
            """
            INSERT INTO queue (day, slot, guid, format, alt_title_1, alt_title_2, post_text, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'planned', datetime('now'))
            ON CONFLICT(day, slot) DO UPDATE SET
              guid=excluded.guid,
              format=excluded.format,
              alt_title_1=excluded.alt_title_1,
              alt_title_2=excluded.alt_title_2,
              post_text=excluded.post_text,
              status='planned',
              error=NULL
            """,
            (day, slot, guid, format, alt_title_1, alt_title_2, post_text),
        )
        con.commit()
        con.close()

    def get_queue_slot(self, day: str, slot: str):
        con = self._conn()
        cur = con.cursor()
        cur.execute(
            "SELECT day, slot, guid, format, alt_title_1, alt_title_2, post_text, status FROM queue WHERE day=? AND slot=?",
            (day, slot),
        )
        row = cur.fetchone()
        con.close()
        if not row:
            return None
        return {
            "day": row[0],
            "slot": row[1],
            "guid": row[2],
            "format": row[3],
            "alt_title_1": row[4],
            "alt_title_2": row[5],
            "post_text": row[6],
            "status": row[7],
        }

    def mark_queue_posted(self, *, day: str, slot: str, tg_message_id: int):
        con = self._conn()
        cur = con.cursor()
        cur.execute(
            "UPDATE queue SET status='posted', tg_message_id=?, posted_at=datetime('now') WHERE day=? AND slot=?",
            (int(tg_message_id), day, slot),
        )
        con.commit()
        con.close()

    def mark_queue_error(self, *, day: str, slot: str, error: str):
        con = self._conn()
        cur = con.cursor()
        cur.execute(
            "UPDATE queue SET status='error', error=? WHERE day=? AND slot=?",
            ((error or "")[:500], day, slot),
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

    def count_items(self):
        con = self._conn()
        cur = con.cursor()
        cur.execute("SELECT COUNT(1) FROM items")
        n = cur.fetchone()[0]
        con.close()
        return int(n)

    def get_recent_posts(self, limit: int = 30):
        con = self._conn()
        cur = con.cursor()
        cur.execute(
            """
            SELECT source, title, link, posted_at
            FROM items
            WHERE posted_at IS NOT NULL
            ORDER BY posted_at DESC
            LIMIT ?
            """,
            (int(limit),),
        )
        rows = cur.fetchall()
        con.close()
        return [
            {"source": r[0], "title": r[1], "link": r[2], "posted_at": r[3]}
            for r in rows
        ]

    def get_metrics_summary(self):
        con = self._conn()
        cur = con.cursor()
        cur.execute("SELECT COUNT(1) FROM items WHERE posted_at IS NOT NULL")
        total_posts = int(cur.fetchone()[0])
        cur.execute(
            """
            SELECT COUNT(1)
            FROM items
            WHERE posted_at IS NOT NULL AND posted_at >= datetime('now', '-1 day')
            """
        )
        posts_last_24h = int(cur.fetchone()[0])
        cur.execute(
            """
            SELECT COALESCE(source,'unknown') AS source, COUNT(1) AS cnt
            FROM items
            WHERE posted_at IS NOT NULL
            GROUP BY COALESCE(source,'unknown')
            ORDER BY cnt DESC
            LIMIT 10
            """
        )
        top_sources = [{"source": r[0], "count": int(r[1])} for r in cur.fetchall()]
        con.close()
        return {
            "total_posts": total_posts,
            "posts_last_24h": posts_last_24h,
            "top_sources": top_sources,
        }

    def add_metric_snapshot(
        self,
        *,
        chat_id: str,
        message_id: int,
        captured_at: str,
        views: int,
        forwards: int,
        replies: int,
        reactions_json: str,
    ):
        con = self._conn()
        cur = con.cursor()
        cur.execute(
            """
            INSERT INTO metrics (captured_at, chat_id, message_id, views, forwards, replies, reactions_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                captured_at,
                str(chat_id),
                int(message_id),
                int(views),
                int(forwards),
                int(replies),
                reactions_json or "{}",
            ),
        )
        con.commit()
        con.close()

    def list_recent_posted_message_ids(self, day: str | None = None, limit: int = 200):
        con = self._conn()
        cur = con.cursor()
        if day:
            cur.execute(
                """
                SELECT tg_message_id
                FROM queue
                WHERE day=? AND status='posted' AND tg_message_id IS NOT NULL
                ORDER BY posted_at DESC
                LIMIT ?
                """,
                (day, int(limit)),
            )
        else:
            cur.execute(
                """
                SELECT tg_message_id
                FROM queue
                WHERE status='posted' AND tg_message_id IS NOT NULL
                ORDER BY posted_at DESC
                LIMIT ?
                """,
                (int(limit),),
            )
        rows = cur.fetchall()
        con.close()
        return [int(r[0]) for r in rows if r and r[0] is not None]

    def get_latest_metrics(self, *, chat_id: str, limit: int = 10):
        con = self._conn()
        cur = con.cursor()
        cur.execute(
            """
            SELECT message_id, captured_at, views, forwards, replies, reactions_json
            FROM metrics
            WHERE chat_id=?
            ORDER BY captured_at DESC
            LIMIT ?
            """,
            (str(chat_id), int(limit)),
        )
        rows = cur.fetchall()
        con.close()
        out = []
        for r in rows:
            out.append(
                {
                    "message_id": r[0],
                    "captured_at": r[1],
                    "views": r[2],
                    "forwards": r[3],
                    "replies": r[4],
                    "reactions_json": r[5],
                }
            )
        return out
