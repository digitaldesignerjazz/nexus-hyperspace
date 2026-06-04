"""Hyperspace-Aware Agent Router + Constellation Manager (M2.1 / M2.2)

Beginning of Phase 2: Intelligent Coordination.

This version integrates with Link Quality Oracle scores and has
smarter (still simple) decision logic + constellation examples.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional, List

from .models import LinkScore


@dataclass
class Constellation:
    name: str
    peers: List[str]
    purpose: str
    created_at: float = field(default_factory=time.time)
    status: str = "active"


class HyperspaceRouter:
    """Decides routing strategy and manages dynamic constellations.

    Integrates Oracle scores for better decisions.
    Lyra modulation influences willingness to use hyperspace.
    """

    def __init__(self, lyra_intensity: float = 5.0):
        self.lyra_intensity = max(0.0, min(10.0, lyra_intensity))
        self.active_constellations: dict[str, Constellation] = {}

    def decide_path(
        self,
        task_type: str = "general",
        local_score: Optional[LinkScore] = None,
        hyperspace_score: Optional[LinkScore] = None,
    ) -> str:
        """Return 'local' or 'hyperspace' based on scores and Lyra bias."""
        if not local_score and not hyperspace_score:
            return "local"

        if local_score and not hyperspace_score:
            return "local"
        if hyperspace_score and not local_score:
            return "hyperspace"

        local_h = local_score.overall_health
        hs_h = hyperspace_score.overall_health

        # Base technical preference
        if local_h > hs_h + 20:
            preference = "local"
        elif hs_h > local_h + 15:
            preference = "hyperspace"
        else:
            # Close call — use Lyra to break tie
            if self.lyra_intensity >= 7.0:
                preference = "hyperspace"  # more adventurous
            elif self.lyra_intensity <= 3.0:
                preference = "local"
            else:
                preference = "hyperspace" if hs_h >= local_h else "local"

        # Task-specific overrides
        if task_type in ("creative", "exploratory", "narrative") and self.lyra_intensity > 5.0:
            if hs_h > 45:
                preference = "hyperspace"

        if task_type in ("consensus", "critical"):
            preference = "local" if local_h > 60 else "hyperspace"

        return preference

    def propose_constellation(
        self,
        name: str,
        peers: List[str],
        purpose: str = "coordination",
    ) -> Constellation:
        constellation = Constellation(name=name, peers=peers, purpose=purpose)
        self.active_constellations[name] = constellation
        return constellation

    def dissolve_constellation(self, name: str) -> bool:
        if name in self.active_constellations:
            self.active_constellations[name].status = "dissolved"
            del self.active_constellations[name]
            return True
        return False

    def get_active_constellations(self) -> List[Constellation]:
        return list(self.active_constellations.values())

    def get_status_summary(self) -> dict:
        return {
            "lyra_intensity": self.lyra_intensity,
            "active_constellations": len(self.active_constellations),
            "constellation_names": list(self.active_constellations.keys()),
        }


# Default instance
router = HyperspaceRouter()
