"""Hyperspace-Aware Agent Router + Constellation Manager (M2.1 / M2.2)

This module is the beginning of Phase 2: Intelligent Coordination.

Core responsibilities:
- Decide when to use local vs hyperspace paths
- Propose, form, and dissolve dynamic "constellations"
- Integrate scores from the Link Quality Oracle
- Support Lyra modulation for creative vs technical routing bias

This is currently a skeleton. Full implementation will come in subsequent iterations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .models import LinkScore


@dataclass
class Constellation:
    name: str
    peers: list[str]
    purpose: str
    created_at: float = field(default_factory=lambda: __import__("time").time())
    status: str = "active"  # active, dissolving, dissolved


class HyperspaceRouter:
    """Decides routing strategy and manages dynamic constellations.

    This is the core of M2.1–M2.2.
    """

    def __init__(self, lyra_intensity: float = 5.0):
        self.lyra_intensity = lyra_intensity  # 0 = pure technical, 10 = highly creative/expressive
        self.active_constellations: dict[str, Constellation] = {}

    def decide_path(
        self,
        task_type: str,
        local_score: Optional[LinkScore] = None,
        hyperspace_score: Optional[LinkScore] = None,
    ) -> str:
        """Decide whether to prefer local or hyperspace path for a task.

        Very basic heuristic for now. Will become much smarter.
        """
        if local_score and hyperspace_score:
            # Simple technical baseline
            if local_score.overall_health > hyperspace_score.overall_health + 15:
                return "local"

            # Lyra modulation: higher Lyra = more willing to use interesting hyperspace peers
            if self.lyra_intensity > 6.0 and hyperspace_score.overall_health > 55:
                return "hyperspace"

            if hyperspace_score.overall_health > local_score.overall_health:
                return "hyperspace"

        return "local"

    def propose_constellation(
        self,
        name: str,
        peers: list[str],
        purpose: str = "coordination",
    ) -> Constellation:
        """Create a new temporary constellation of hyperspace peers."""
        constellation = Constellation(name=name, peers=peers, purpose=purpose)
        self.active_constellations[name] = constellation
        return constellation

    def dissolve_constellation(self, name: str) -> bool:
        if name in self.active_constellations:
            self.active_constellations[name].status = "dissolved"
            del self.active_constellations[name]
            return True
        return False

    def get_active_constellations(self) -> list[Constellation]:
        return list(self.active_constellations.values())


# Convenience instance
router = HyperspaceRouter()
