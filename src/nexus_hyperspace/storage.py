"""Simple persistent storage for the Link Quality Oracle using SQLite.

Stores metrics and computed scores so the Oracle can build history and
reputation over time (key for M1.1 success metrics and later reputation memory).

This is a lightweight foundation — can later be extended or replaced with
more sophisticated time-series storage.
"""

import sqlite3
from pathlib import Path
from typing import Optional


class OracleStorage:
    """SQLite-backed storage for link metrics and scores."""

    def __init__(self, db_path: str = "data/oracle.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._create_tables()

    def _create_tables(self):
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                peer_id TEXT NOT NULL,
                latency_ms REAL,
                packet_loss_percent REAL,
                jitter_ms REAL,
                timestamp REAL DEFAULT (strftime('%s','now'))
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS scores (
                peer_id TEXT PRIMARY KEY,
                overall_health REAL,
                latency_score REAL,
                stability_score REAL,
                confidence REAL,
                classification TEXT,
                last_updated REAL DEFAULT (strftime('%s','now'))
            )
        """)
        self._conn.commit()

    def record_metric(self, peer_id: str, latency_ms: float, packet_loss_percent: float, jitter_ms: float = 0.0):
        self._conn.execute(
            "INSERT INTO metrics (peer_id, latency_ms, packet_loss_percent, jitter_ms) VALUES (?, ?, ?, ?)",
            (peer_id, latency_ms, packet_loss_percent, jitter_ms)
        )
        self._conn.commit()

    def save_score(self, peer_id: str, overall_health: float, latency_score: float,
                   stability_score: float, confidence: float, classification: str):
        self._conn.execute("""
            INSERT OR REPLACE INTO scores
            (peer_id, overall_health, latency_score, stability_score, confidence, classification)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (peer_id, overall_health, latency_score, stability_score, confidence, classification))
        self._conn.commit()

    def get_recent_metrics(self, peer_id: str, limit: int = 20):
        cur = self._conn.execute(
            "SELECT latency_ms, packet_loss_percent, jitter_ms, timestamp FROM metrics "
            "WHERE peer_id = ? ORDER BY timestamp DESC LIMIT ?",
            (peer_id, limit)
        )
        return cur.fetchall()

    def get_all_scores(self):
        cur = self._conn.execute(
            "SELECT peer_id, overall_health, latency_score, stability_score, confidence, classification, last_updated FROM scores"
        )
        return cur.fetchall()

    def close(self):
        self._conn.close()
