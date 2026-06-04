"""Tests for the PeerClassifier (M1.2)."""

import pytest

from nexus_hyperspace.peer_classifier import PeerClassifier, classify_peer
from nexus_hyperspace.models import LinkScore


def test_classify_excellent_peer():
    score = LinkScore(
        peer_id="test-peer",
        overall_health=90.0,
        latency_score=92.0,
        stability_score=88.0,
        confidence=0.8,
        classification="Local-Multicast",
    )
    result = classify_peer("test-peer", current_score=score)
    assert result.category == "Local-Multicast"
    assert result.confidence > 0.85
    assert "coordination" in result.recommended_for


def test_classify_volatile_peer():
    score = LinkScore(
        peer_id="test-peer",
        overall_health=55.0,
        latency_score=50.0,
        stability_score=48.0,
        confidence=0.5,
        classification="Hyperspace-Volatile",
    )
    result = classify_peer("test-peer", current_score=score)
    assert result.category == "Hyperspace-Volatile"
    assert result.confidence >= 0.55


def test_classify_no_score():
    result = classify_peer("unknown-peer", current_score=None)
    assert result.category == "Emerging"
    assert result.confidence < 0.5
