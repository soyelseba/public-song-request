"""Persistencia SQLite de peticiones y ajustes."""
from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS requests (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    query       TEXT NOT NULL,
    platform    TEXT,
    title       TEXT,
    artist      TEXT,
    thumbnail   TEXT,
    duration    REAL,
    webpage_url TEXT,
    guest_name  TEXT,
    guest_id    TEXT,
    guest_ip    TEXT,
    status      TEXT NOT NULL,
    position    REAL,
    error       TEXT,
    file_path   TEXT,
    created_at  REAL,
    updated_at  REAL,
    played_at   REAL
);
CREATE INDEX IF NOT EXISTS idx_requests_status ON requests(status);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
"""

# Estados:
#   resolving   -> buscando metadatos
#   pending     -> esperando aprobación del admin
#   approved    -> aprobada, esperando descarga
#   downloading -> descargando audio
#   ready       -> lista en la cola
#   playing     -> sonando
#   played / rejected / error -> finalizadas
QUEUE_STATUSES = ("approved", "downloading", "ready")
ACTIVE_STATUSES = ("resolving", "pending", *QUEUE_STATUSES, "playing")
FINISHED_STATUSES = ("played", "rejected", "error")

DEFAULT_SETTINGS = {
    "requests_open": "1",
    "auto_approve": "0",
    "player_mode": "browser",
    "volume": "80",
    "server_ip": "",
}

UPDATABLE = {
    "query", "platform", "title", "artist", "thumbnail", "duration", "webpage_url",
    "guest_name", "status", "position", "error", "file_path", "played_at",
}

PUBLIC_FIELDS = (
    "id", "platform", "title", "artist", "thumbnail", "duration",
    "guest_name", "status", "position", "error", "created_at",
)
ADMIN_FIELDS = PUBLIC_FIELDS + ("query", "webpage_url", "guest_ip", "guest_id")


def public_view(row: dict | None, admin: bool = False, progress: float | None = None) -> dict | None:
    if not row:
        return None
    fields = ADMIN_FIELDS if admin else PUBLIC_FIELDS
    data = {k: row.get(k) for k in fields}
    if progress is not None:
        data["progress"] = round(progress, 1)
    return data


def _marks(n: int) -> str:
    return ",".join("?" * n)


class Database:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        with self.lock:
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.executescript(SCHEMA)
            for k, v in DEFAULT_SETTINGS.items():
                self.conn.execute("INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)", (k, v))
            self.conn.commit()

    # ---- helpers -------------------------------------------------------
    def _exec(self, sql: str, params: tuple = ()) -> int:
        with self.lock:
            cur = self.conn.execute(sql, params)
            self.conn.commit()
            return cur.lastrowid

    def _all(self, sql: str, params: tuple = ()) -> list[dict]:
        with self.lock:
            return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def _one(self, sql: str, params: tuple = ()) -> dict | None:
        with self.lock:
            row = self.conn.execute(sql, params).fetchone()
            return dict(row) if row else None

    # ---- requests ------------------------------------------------------
    def create_request(self, *, query: str, platform: str, guest_name: str, guest_id: str, guest_ip: str) -> int:
        now = time.time()
        return self._exec(
            "INSERT INTO requests(query, platform, guest_name, guest_id, guest_ip, status, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, 'resolving', ?, ?)",
            (query, platform, guest_name, guest_id, guest_ip, now, now),
        )

    def update_request(self, rid: int, **fields: Any) -> None:
        fields = {k: v for k, v in fields.items() if k in UPDATABLE}
        if not fields:
            return
        fields["updated_at"] = time.time()
        cols = ", ".join(f"{k} = ?" for k in fields)
        self._exec(f"UPDATE requests SET {cols} WHERE id = ?", (*fields.values(), rid))

    def get_request(self, rid: int | None) -> dict | None:
        if rid is None:
            return None
        return self._one("SELECT * FROM requests WHERE id = ?", (rid,))

    def delete_request(self, rid: int) -> None:
        self._exec("DELETE FROM requests WHERE id = ?", (rid,))

    def requests_with_status(self, *statuses: str) -> list[dict]:
        return self._all(
            f"SELECT * FROM requests WHERE status IN ({_marks(len(statuses))}) ORDER BY created_at",
            statuses,
        )

    def active_requests(self) -> list[dict]:
        return self._all(
            f"SELECT * FROM requests WHERE status IN ({_marks(len(ACTIVE_STATUSES))})"
            " ORDER BY CASE WHEN position IS NULL THEN 1 ELSE 0 END, position, created_at",
            ACTIVE_STATUSES,
        )

    def recent_finished(self, limit: int = 30) -> list[dict]:
        return self._all(
            f"SELECT * FROM requests WHERE status IN ({_marks(len(FINISHED_STATUSES))})"
            " ORDER BY updated_at DESC LIMIT ?",
            (*FINISHED_STATUSES, limit),
        )

    def queue_items(self) -> list[dict]:
        return self._all(
            f"SELECT * FROM requests WHERE status IN ({_marks(len(QUEUE_STATUSES))}) ORDER BY position, created_at",
            QUEUE_STATUSES,
        )

    def next_ready(self) -> dict | None:
        return self._one("SELECT * FROM requests WHERE status = 'ready' ORDER BY position, created_at LIMIT 1")

    def next_position(self) -> float:
        row = self._one(
            f"SELECT MAX(position) AS p FROM requests WHERE status IN ({_marks(len(QUEUE_STATUSES))})",
            QUEUE_STATUSES,
        )
        return (row["p"] or 0) + 1

    def top_position(self) -> float:
        row = self._one(
            f"SELECT MIN(position) AS p FROM requests WHERE status IN ({_marks(len(QUEUE_STATUSES))})",
            QUEUE_STATUSES,
        )
        return (row["p"] if row and row["p"] is not None else 1) - 1

    def count_open_for_guest(self, guest_id: str) -> int:
        row = self._one(
            "SELECT COUNT(*) AS n FROM requests WHERE status IN ('resolving', 'pending') AND guest_id = ?",
            (guest_id,),
        )
        return row["n"] if row else 0

    def find_active_duplicate(self, webpage_url: str, exclude_id: int) -> dict | None:
        statuses = tuple(s for s in ACTIVE_STATUSES if s != "resolving")
        return self._one(
            f"SELECT * FROM requests WHERE webpage_url = ? AND id != ? AND status IN ({_marks(len(statuses))}) LIMIT 1",
            (webpage_url, exclude_id, *statuses),
        )

    def clear_history(self) -> None:
        self._exec(f"DELETE FROM requests WHERE status IN ({_marks(len(FINISHED_STATUSES))})", FINISHED_STATUSES)

    # ---- settings ------------------------------------------------------
    def get_setting(self, key: str, default: str | None = None) -> str | None:
        row = self._one("SELECT value FROM settings WHERE key = ?", (key,))
        return row["value"] if row else (default if default is not None else DEFAULT_SETTINGS.get(key))

    def set_setting(self, key: str, value: Any) -> None:
        self._exec("INSERT OR REPLACE INTO settings(key, value) VALUES (?, ?)", (key, str(value)))
