from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


class Database:
    def __init__(self, path: Path):
        self.path = path
        self._init_db()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS seen_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    link TEXT UNIQUE NOT NULL,
                    title TEXT,
                    source TEXT,
                    published TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )

    def is_seen(self, link: str) -> bool:
        with self.connection() as conn:
            row = conn.execute("SELECT 1 FROM seen_items WHERE link = ?", (link,)).fetchone()
            return row is not None

    def is_seen_title_source(self, title: str, source: str) -> bool:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM seen_items WHERE title = ? AND source = ? LIMIT 1",
                (title, source),
            ).fetchone()
            return row is not None

    def mark_seen(self, link: str, title: str, source: str, published: str) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO seen_items(link, title, source, published)
                VALUES (?, ?, ?, ?)
                """,
                (link, title, source, published),
            )

    def set_setting(self, key: str, value: str) -> None:
        with self.connection() as conn:
            conn.execute(
                "INSERT INTO settings(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    def get_setting(self, key: str) -> str | None:
        with self.connection() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
            return None if row is None else str(row["value"])

    def get_recent_items(self, limit: int = 20) -> list[dict[str, str]]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT title, link, source, published, created_at
                FROM seen_items
                ORDER BY datetime(created_at) DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_metrics(self) -> dict[str, object]:
        with self.connection() as conn:
            totals = conn.execute("SELECT COUNT(*) AS value FROM seen_items").fetchone()
            last24h = conn.execute(
                """
                SELECT COUNT(*) AS value
                FROM seen_items
                WHERE datetime(created_at) >= datetime('now', '-1 day')
                """
            ).fetchone()
            sources = conn.execute(
                """
                SELECT COALESCE(source, 'unknown') AS source, COUNT(*) AS count
                FROM seen_items
                GROUP BY source
                ORDER BY count DESC
                LIMIT 10
                """
            ).fetchall()

        return {
            "total_posts": int(totals["value"] if totals else 0),
            "posts_last_24h": int(last24h["value"] if last24h else 0),
            "top_sources": [dict(row) for row in sources],
        }
