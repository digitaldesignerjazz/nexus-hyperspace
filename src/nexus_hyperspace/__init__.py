"""Nexus Hyperspace

Advanced hyperspace peering, long-distance Yggdrasil mesh coordination,
Nexus AI agent swarm integration, and decentralized infrastructure protocols.

Part of the broader NovaNet / xMesh / QNET vision.
"""

__version__ = "0.1.0"

try:
    from .oracle import HyperspaceLinkQualityOracle
    from .models import LinkMetrics, LinkScore, PeerClassification
    from .yggdrasil_client import YggdrasilAdminClient
    from .storage import OracleStorage
    from .peer_classifier import PeerClassifier, classify_peer, ClassificationResult
except ImportError:
    pass

__all__ = [
    "HyperspaceLinkQualityOracle",
    "LinkMetrics",
    "LinkScore",
    "PeerClassification",
    "YggdrasilAdminClient",
    "OracleStorage",
    "PeerClassifier",
    "classify_peer",
    "ClassificationResult",
    "__version__",
]
