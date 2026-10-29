"""SQLite: канонічна таблиця posts, курсори цілей, журнал запитів і прогонів."""
import json
import sqlite3
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
    uid          TEXT PRIMARY KEY,      -- sha256(platform|uri): ключ dedup, однаковий для поста на будь-якому інстансі
    platform     TEXT NOT NULL,
    instance     TEXT NOT NULL,
    source_id    TEXT NOT NULL,         -- id статусу на інстансі (курсор)
    author       TEXT NOT NULL,         -- user@domain
    author_url   TEXT,
    url          TEXT NOT NULL,
    date         TEXT NOT NULL,         -- ISO-8601 UTC
    text         TEXT NOT NULL,
    lang         TEXT,
    media        TEXT NOT NULL DEFAULT '[]',
    query        TEXT NOT NULL,         -- ціль, з якої вперше зібрано
    collected_at TEXT NOT NULL,
    collector    TEXT NOT NULL,
    raw          TEXT NOT NULL,         -- сирий JSON відповіді для аудиту
    UNIQUE (instance, source_id)
);
CREATE INDEX IF NOT EXISTS posts_date ON posts (date);
CREATE TABLE IF NOT EXISTS cursors (
    target        TEXT PRIMARY KEY,
    min_id        TEXT,                 -- найновіший зібраний id → наступний інкрементний прогін
    max_id        TEXT,                 -- найстаріший зібраний id → backfill
    backfill_done INTEGER NOT NULL DEFAULT 0,
    status        TEXT NOT NULL DEFAULT 'new',
    last_error    TEXT,
    updated_at    TEXT
);
CREATE TABLE IF NOT EXISTS requests (
    ts TEXT, host TEXT, path TEXT, status INTEGER, rl_limit TEXT, rl_remaining TEXT,
    rl_reset TEXT, retry_after TEXT, elapsed_ms INTEGER, error TEXT
);
CREATE TABLE IF NOT EXISTS runs (
    started_at TEXT, finished_at TEXT, mode TEXT, target TEXT, pages INTEGER, fetched INTEGER,
    inserted INTEGER, duplicates INTEGER, skipped INTEGER, status TEXT, error TEXT
);
"""

POST_FIELDS = ("uid", "platform", "instance", "source_id", "author", "author_url", "url", "date", "text",
               "lang", "media", "query", "collected_at", "collector", "raw")
EXPORT_FIELDS = tuple(f for f in POST_FIELDS if f != "raw")


def id_key(status_id):
    """Порядок id статусів: Mastodon — числові рядки, Pleroma/GoToSocial — рядки фіксованої довжини."""
    return len(status_id), status_id


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class Store:
    def __init__(self, path):
        self.conn = sqlite3.connect(path, timeout=30)  # docker-цикл і ручний запуск можуть збігтися
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    def cursor(self, target):
        row = self.conn.execute("SELECT * FROM cursors WHERE target = ?", (target,)).fetchone()
        return dict(row) if row else {"target": target, "min_id": None, "max_id": None, "backfill_done": 0}

    def save_page(self, target, rows, newest_id, oldest_id):
        """Пачка + зсув курсора в ОДНІЙ транзакції: курсор не випереджає записані дані."""
        cur = self.cursor(target)
        min_id = max(filter(None, (newest_id, cur["min_id"])), key=id_key)
        max_id = min(filter(None, (oldest_id, cur["max_id"])), key=id_key)
        with self.conn:
            before = self.conn.total_changes
            self.conn.executemany(
                f"INSERT OR IGNORE INTO posts ({','.join(POST_FIELDS)}) VALUES ({','.join('?' * len(POST_FIELDS))})",
                [tuple(r[f] for f in POST_FIELDS) for r in rows])
            inserted = self.conn.total_changes - before
            self.conn.execute(
                "INSERT INTO cursors (target, min_id, max_id, status, updated_at) VALUES (?, ?, ?, 'ok', ?) "
                "ON CONFLICT(target) DO UPDATE SET min_id = excluded.min_id, max_id = excluded.max_id, "
                "status = 'ok', last_error = NULL, updated_at = excluded.updated_at",
                (target, min_id, max_id, utc_now()))
        return inserted

    def mark(self, target, status, error=None, backfill_done=None):
        with self.conn:
            self.conn.execute("INSERT OR IGNORE INTO cursors (target) VALUES (?)", (target,))
            self.conn.execute("UPDATE cursors SET status = ?, last_error = ?, updated_at = ?, "
                              "backfill_done = COALESCE(?, backfill_done) WHERE target = ?",
                              (status, error, utc_now(), backfill_done, target))

    def log_request(self, **kw):
        with self.conn:
            self.conn.execute("INSERT INTO requests VALUES (?,?,?,?,?,?,?,?,?,?)",
                              (utc_now(), kw["host"], kw["path"], kw["status"], kw["rl_limit"],
                               kw["rl_remaining"], kw["rl_reset"], kw["retry_after"], kw["elapsed_ms"], kw["error"]))

    def log_run(self, **kw):
        with self.conn:
            self.conn.execute("INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                              (kw["started_at"], utc_now(), kw["mode"], kw["target"], kw["pages"], kw["fetched"],
                               kw["inserted"], kw["duplicates"], kw["skipped"], kw["status"], kw.get("error")))

    def iter_posts(self):
        for row in self.conn.execute(f"SELECT {','.join(EXPORT_FIELDS)} FROM posts ORDER BY date, uid"):
            item = dict(row)
            item["media"] = json.loads(item["media"])
            yield item

    def query(self, sql, params=()):
        return [dict(r) for r in self.conn.execute(sql, params)]
