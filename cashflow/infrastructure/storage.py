"""SQLite adapters for the local deployment; each service owns its database."""

import hashlib
import json
import random
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path

from cashflow.domain.model import Conflict, Entry, validate_event


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class Database:
    def __init__(self, path):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.execute("PRAGMA journal_mode=WAL")

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA synchronous=FULL")
        try:
            with db:
                yield db
        finally:
            db.close()

    def health(self):
        with self.connection() as db:
            db.execute("SELECT 1").fetchone()


class LedgerStore(Database):
    def __init__(self, path):
        super().__init__(path)
        with self.connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS entries(
                    id TEXT PRIMARY KEY, request_key TEXT UNIQUE NOT NULL,
                    fingerprint TEXT NOT NULL, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS outbox(
                    id TEXT PRIMARY KEY, payload TEXT NOT NULL,
                    created REAL NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
                    next_attempt REAL NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'pending');
                CREATE INDEX IF NOT EXISTS ix_outbox_due ON outbox(status, next_attempt);
            """)

    def record(self, entry: Entry, key: str):
        data = asdict(entry)
        business = {k: v for k, v in data.items() if k not in ("id", "created_at")}
        fingerprint = hashlib.sha256(canonical(business).encode()).hexdigest()
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute("SELECT * FROM entries WHERE request_key=?", (key,)).fetchone()
            if previous:
                if previous["fingerprint"] != fingerprint:
                    raise Conflict("Idempotency-Key reused with different content")
                return json.loads(previous["payload"]), True
            db.execute(
                "INSERT INTO entries VALUES (?,?,?,?)",
                (entry.id, key, fingerprint, canonical(data)),
            )
            db.execute(
                "INSERT INTO outbox(id,payload,created) VALUES (?,?,?)",
                (entry.id, canonical(entry.event()), time.time()),
            )
        return data, False

    def get(self, entry_id):
        with self.connection() as db:
            row = db.execute("SELECT payload FROM entries WHERE id=?", (entry_id,)).fetchone()
        return json.loads(row["payload"]) if row else None

    def due(self, limit=100):
        with self.connection() as db:
            return [
                dict(row)
                for row in db.execute(
                    "SELECT * FROM outbox WHERE status='pending' AND next_attempt<=? "
                    "ORDER BY created LIMIT ?",
                    (time.time(), limit),
                )
            ]

    def delivered(self, event_id):
        with self.connection() as db:
            db.execute("UPDATE outbox SET status='delivered' WHERE id=?", (event_id,))

    def failed(self, event_id, attempts, permanent=False):
        delay = min(60, 2 ** min(attempts, 6)) + random.uniform(0, 1)
        with self.connection() as db:
            db.execute(
                "UPDATE outbox SET attempts=?, next_attempt=?, status=? "
                "WHERE id=? AND status='pending'",
                (
                    attempts + 1,
                    time.time() + delay,
                    "quarantined" if permanent else "pending",
                    event_id,
                ),
            )

    def stats(self):
        with self.connection() as db:
            counts = {
                row["status"]: row["n"]
                for row in db.execute("SELECT status, COUNT(*) n FROM outbox GROUP BY status")
            }
            oldest = db.execute(
                "SELECT MIN(created) FROM outbox WHERE status='pending'"
            ).fetchone()[0]
        return {
            "pending": counts.get("pending", 0),
            "quarantined": counts.get("quarantined", 0),
            "oldest_pending_seconds": max(0, time.time() - oldest) if oldest else 0,
        }


class SummaryStore(Database):
    def __init__(self, path):
        super().__init__(path)
        with self.connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS inbox(
                    id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, received_at REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS daily(
                    day TEXT PRIMARY KEY, credits INTEGER NOT NULL DEFAULT 0,
                    debits INTEGER NOT NULL DEFAULT 0, count INTEGER NOT NULL DEFAULT 0);
            """)

    def consume(self, event):
        entry = validate_event(event)
        digest = hashlib.sha256(canonical(event).encode()).hexdigest()
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                "SELECT fingerprint FROM inbox WHERE id=?", (entry.id,)
            ).fetchone()
            if existing:
                if existing["fingerprint"] != digest:
                    raise Conflict("event identity reused with different content")
                return False
            db.execute("INSERT INTO inbox VALUES (?,?,?)", (entry.id, digest, time.time()))
            credits = entry.amount_cents if entry.kind == "credit" else 0
            debits = entry.amount_cents if entry.kind == "debit" else 0
            db.execute(
                "INSERT INTO daily(day,credits,debits,count) VALUES (?,?,?,1) "
                "ON CONFLICT(day) DO UPDATE SET credits=credits+excluded.credits, "
                "debits=debits+excluded.debits, count=count+1",
                (entry.business_date, credits, debits),
            )
        return True

    def report(self, day):
        with self.connection() as db:
            db.execute("BEGIN")  # Opening, daily and watermark share one read snapshot.
            opening = db.execute(
                "SELECT COALESCE(SUM(credits-debits),0) FROM daily WHERE day<?", (day,)
            ).fetchone()[0]
            row = db.execute("SELECT * FROM daily WHERE day=?", (day,)).fetchone()
            last = db.execute("SELECT MAX(received_at) FROM inbox").fetchone()[0]
        credits, debits, count = (row["credits"], row["debits"], row["count"]) if row else (0, 0, 0)
        return {
            "business_date": day,
            "currency": "BRL",
            "opening_cents": opening,
            "credits_cents": credits,
            "debits_cents": debits,
            "net_cents": credits - debits,
            "closing_cents": opening + credits - debits,
            "entry_count": count,
            "consistency": "eventual",
            "last_event_received_at_epoch": last,
        }
