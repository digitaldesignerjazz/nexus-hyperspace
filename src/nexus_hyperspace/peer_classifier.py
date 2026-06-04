"""Peer Classification Engine (M1.2)

Improved classification logic with confidence scoring.
This module separates classification concerns from the Link Quality Oracle
as described in ARCHITECTURE.md and the Roadmap.

Classification categories:
  - Local-Multicast
  - Hyperspace-Stable
  - Hyperspace-Volatile
  - Emerging

Future enhancements: context-aware classification, reputation memory,
and Lyra-modulated preferences.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import LinkScore


@dataclass
class ClassificationResult:
    category: str
    confidence: float
    rationale: str
    recommended_for: list[str]


class PeerClassifier:
    """Improved peer classification with better heuristics."""

    def classify(
        self,
        peer_id: str,
        current_score: LinkScore | None = None,
        recent_latencies: list[float] | None = None,
        recent_losses: list[float] | None = None,
        historical_uptime: float = 0.0,
    ) -> ClassificationResult:
        if current_score is None:
            return ClassificationResult(
                category="Emerging",
                confidence=0.3,
                rationale="No score data available yet",
                recommended_for=["probation"],
            )

        latency = current_score.latency_score  # higher is better (we invert conceptually)
        stability = current_score.stability_score
        overall = current_score.overall_health
        data_points = len(recent_latencies) if recent_latencies else 5

        # Base classification on current performance
        if overall >= 85 and stability >= 80:
            category = "Local-Multicast"
            rationale = "Excellent low latency + high stability"
            recommended_for = ["coordination", "creative-swarm", "high-trust"]
            base_conf = 0.9
        elif overall >= 70 and stability >= 65:
            category = "Hyperspace-Stable"
            rationale = "Good performance for long-distance link"
            recommended_for = ["coordination", "backbone", "reliable-tasks"]
            base_conf = 0.75
        elif overall >= 50 and stability >= 45:
            category = "Hyperspace-Volatile"
            rationale = "Usable but variable performance"
            recommended_for = ["burst-capacity", "geographic-diversity", "low-priority"]
            base_conf = 0.6
        else:
            category = "Emerging"
            rationale = "Poor or insufficient data"
            recommended_for = ["probation", "monitoring"]
            base_conf = 0.4

        # Boost confidence with more data points
        confidence = min(0.95, base_conf + (data_points * 0.04))

        # Adjust for historical uptime if available
        if historical_uptime > 3600 * 24:  # > 1 day
            confidence = min(0.97, confidence + 0.1)
            if category == "Hyperspace-Volatile":
                rationale += " (long uptime improves confidence)"

        return ClassificationResult(
            category=category,
            confidence=round(confidence, 2),
            rationale=rationale,
            recommended_for=recommended_for,
        )


# Convenience function for direct use
_classifier = PeerClassifier()

def classify_peer(
    peer_id: str,
    current_score: LinkScore | None = None,
    recent_latencies: list[float] | None = None,
    recent_losses: list[float] | None = None,
    historical_uptime: float = 0.0,
) -> ClassificationResult:
    return _classifier.classify(
        peer_id, current_score, recent_latencies, recent_losses, historical_uptime
    )
