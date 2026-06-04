"""Nexus Hyperspace

Advanced hyperspace peering, long-distance Yggdrasil mesh coordination,
Nexus AI agent swarm integration, and decentralized infrastructure protocols.

Part of the broader NovaNet / xMesh / QNET vision.
"""

__version__ = "0.1.0"

# Core exports for easy importing
try:
    from .oracle import HyperspaceLinkQualityOracle
    from .models import LinkMetrics, LinkScore, PeerClassification
except ImportError:
    # Allow package import even if submodules have issues during early development
    pass

__all__ = [
    "HyperspaceLinkQualityOracle",
    "LinkMetrics",
    "LinkScore",
    "PeerClassification",
    "__version__",
]
