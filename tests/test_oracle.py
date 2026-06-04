"""Tests for HyperspaceLinkQualityOracle core functionality."""

import pytest

from nexus_hyperspace.oracle import HyperspaceLinkQualityOracle


def test_oracle_records_and_scores():
    oracle = HyperspaceLinkQualityOracle(persist=False)

    score = oracle.record_metrics("test-peer-1", latency_ms=35.0, packet_loss_percent=0.3)

    assert score is not None
    assert score.overall_health > 70
    assert score.latency_score > 80
    assert score.classification in ["Local-Multicast", "Hyperspace-Stable"]


def test_oracle_multiple_observations():
    oracle = HyperspaceLinkQualityOracle(persist=False)

    for i in range(6):
        oracle.record_metrics("peer-2", latency_ms=50 + i * 2, packet_loss_percent=1.0)

    score = oracle.get_score("peer-2")
    assert score is not None
    assert score.confidence > 0.6  # confidence grows with data


def test_oracle_demo_runs_without_error():
    oracle = HyperspaceLinkQualityOracle(persist=False)
    # Should not raise
    oracle.demo_run(num_peers=3, prefer_live=False)
