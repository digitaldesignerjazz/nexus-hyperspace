"""Data models for Nexus Hyperspace components (Link Quality Oracle, Peer Classification, etc.)."""

from dataclasses import dataclass, field
from typing import Optional
import time


@dataclass
class LinkMetrics:
    """Raw metrics recorded for a single hyperspace (or local) peer link."""
    peer_id: str
    latency_ms: float
    packet_loss_percent: float  # 0.0 - 100.0
    jitter_ms: float = 0.0
    throughput_mbps: Optional[float] = None
    uptime_seconds: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class LinkScore:
    """Computed health scores for a peer link."""
    peer_id: str
    overall_health: float      # 0-100
    latency_score: float       # 0-100 (lower latency = higher score)
    stability_score: float     # 0-100 (low loss + low flapping)
    confidence: float = 0.5    # 0-1, increases with more data points
    last_updated: float = field(default_factory=time.time)
    classification: str = "unknown"  # Local, Hyperspace-Stable, Hyperspace-Volatile, Emerging


@dataclass
class PeerClassification:
    """Classification result for a peer."""
    peer_id: str
    category: str  # Local-Multicast | Hyperspace-Stable | Hyperspace-Volatile | Emerging
    confidence: float
    rationale: str
    recommended_for: list[str] = field(default_factory=list)  # e.g. ["coordination", "creative-swarm", "high-bandwidth"]
