"""Tests for HyperspaceRouter (M2.1/M2.2)."""

import pytest

from nexus_hyperspace.router import HyperspaceRouter
from nexus_hyperspace.models import LinkScore


def test_decide_path_prefers_local_when_much_better():
    router = HyperspaceRouter(lyra_intensity=5.0)
    local = LinkScore("local", 92.0, 90.0, 88.0, 0.9, "Local-Multicast")
    hs = LinkScore("hs", 65.0, 60.0, 70.0, 0.7, "Hyperspace-Stable")

    decision = router.decide_path("general", local, hs)
    assert decision == "local"


def test_decide_path_prefers_hyperspace_when_lyra_high():
    router = HyperspaceRouter(lyra_intensity=8.0)
    local = LinkScore("local", 70.0, 68.0, 72.0, 0.8, "Local-Multicast")
    hs = LinkScore("hs", 68.0, 65.0, 70.0, 0.75, "Hyperspace-Stable")

    decision = router.decide_path("general", local, hs)
    assert decision == "hyperspace"


def test_decide_path_creative_task_with_high_lyra():
    router = HyperspaceRouter(lyra_intensity=7.5)
    local = LinkScore("local", 80.0, 78.0, 82.0, 0.85, "Local-Multicast")
    hs = LinkScore("hs", 62.0, 58.0, 65.0, 0.7, "Hyperspace-Volatile")

    decision = router.decide_path("creative", local, hs)
    assert decision == "hyperspace"


def test_constellation_lifecycle():
    router = HyperspaceRouter()
    const = router.propose_constellation("test-const", ["p1", "p2"], "coordination")

    assert const.name == "test-const"
    assert len(router.get_active_constellations()) == 1

    dissolved = router.dissolve_constellation("test-const")
    assert dissolved is True
    assert len(router.get_active_constellations()) == 0


def test_status_summary():
    router = HyperspaceRouter(lyra_intensity=6.5)
    router.propose_constellation("c1", ["a", "b"])

    summary = router.get_status_summary()
    assert summary["lyra_intensity"] == 6.5
    assert summary["active_constellations"] == 1
