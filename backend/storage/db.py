"""SQLite 存储：jobs 与 events。"""

from __future__ import annotations

import sqlite3
import time
import uuid
from pathlib import Path


class Database:
    def __init__(self, path: Path | str) -> None:
        self.path = str(path)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    ticker TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'queued',
                    created_at TEXT NOT NULL,
                    finished_at TEXT,
                    report_path TEXT
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    seq INTEGER NOT NULL,
                    ts TEXT NOT NULL,
                    type TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_events_job ON events(job_id, seq);
                """
            )

    def create_job(self, params: dict) -> str:
        job_id = uuid.uuid4().hex[:16]
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO jobs (id, ticker, mode, status, created_at) VALUES (?, ?, ?, 'queued', ?)",
                (job_id, params.get("ticker", ""), params.get("mode", "mock"), time.strftime("%Y-%m-%dT%H:%M:%S")),
            )
        return job_id

    def update_job_status(self, job_id: str, status: str, report_path: str | None = None) -> None:
        with self._connect() as conn:
            if status in ("succeeded", "failed"):
                conn.execute(
                    "UPDATE jobs SET status = ?, finished_at = ?, report_path = COALESCE(?, report_path) WHERE id = ?",
                    (status, time.strftime("%Y-%m-%dT%H:%M:%S"), report_path, job_id),
                )
            else:
                conn.execute("UPDATE jobs SET status = ? WHERE id = ?", (status, job_id))

    def get_job(self, job_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return dict(row) if row else None

    def append_event(self, event: dict) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO events (job_id, seq, ts, type, payload) VALUES (?, ?, ?, ?, ?)",
                (
                    event["job_id"],
                    event["seq"],
                    event["ts"],
                    event["type"],
                    __import__("json").dumps(event["payload"], ensure_ascii=False),
                ),
            )

    def list_events(self, job_id: str) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT seq, ts, type, payload FROM events WHERE job_id = ? ORDER BY seq",
                (job_id,),
            ).fetchall()
        return [
            {
                "job_id": job_id,
                "seq": r["seq"],
                "ts": r["ts"],
                "type": r["type"],
                "payload": __import__("json").loads(r["payload"]),
            }
            for r in rows
        ]
