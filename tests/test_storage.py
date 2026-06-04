"""Tests for OracleStorage."""

import tempfile
import os

import pytest

from nexus_hyperspace.storage import OracleStorage


def test_storage_record_and_retrieve():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_oracle.db")
        storage = OracleStorage(db_path=db_path)

        storage.record_metric("peer-123", latency_ms=45.2, packet_loss_percent=0.8)
        storage.save_score(
            peer_id="peer-123",
            overall_health=82.5,
            latency_score=85.0,
            stability_score=79.0,
            confidence=0.75,
            classification="Hyperspace-Stable",
        )

        metrics = storage.get_recent_metrics("peer-123", limit=5)
        scores = storage.get_all_scores()

        assert len(metrics) >= 1
        assert any(s[0] == "peer-123" for s in scores)

        storage.close()
