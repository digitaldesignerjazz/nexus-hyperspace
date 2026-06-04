"""Hyperspace Link Quality Oracle (M1.1)

Real-time and historical scoring of Yggdrasil hyperspace (and local) peer links.
Provides trusted signals for the Nexus agent router and constellation manager.

This is an early prototype implementing core concepts from ARCHITECTURE.md.
"""

from __future__ import annotations

import time
import random
from collections import defaultdict
from statistics import mean, stdev

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

try:
    from .models import LinkMetrics, LinkScore
except ImportError:
    # Fallback for direct script execution during early dev
    from models import LinkMetrics, LinkScore  # type: ignore


class HyperspaceLinkQualityOracle:
    """Core component for recording metrics and computing link health scores.

    Uses simple EWMA-style scoring + rule-based classification for the prototype.
    Future versions will add:
    - Persistent storage (SQLite)
    - Real Yggdrasil admin socket polling
    - Time-series forecasting
    - Integration with Nexus agent swarm via gRPC/HTTP
    """

    def __init__(self, ewma_alpha: float = 0.3):
        self.ewma_alpha = ewma_alpha
        self._history: dict[str, list[LinkMetrics]] = defaultdict(list)
        self._scores: dict[str, LinkScore] = {}
        self.console = Console() if RICH_AVAILABLE else None

    def record_metrics(
        self,
        peer_id: str,
        latency_ms: float,
        packet_loss_percent: float,
        jitter_ms: float = 0.0,
    ) -> LinkScore:
        """Record a new observation and recompute the score for the peer."""
        metrics = LinkMetrics(
            peer_id=peer_id,
            latency_ms=latency_ms,
            packet_loss_percent=packet_loss_percent,
            jitter_ms=jitter_ms,
        )
        self._history[peer_id].append(metrics)
        return self._recalculate_score(peer_id)

    def _recalculate_score(self, peer_id: str) -> LinkScore:
        history = self._history[peer_id]
        if not history:
            return self._default_score(peer_id)

        n = min(len(history), 8)
        recent = history[-n:]

        latencies = [m.latency_ms for m in recent]
        losses = [m.packet_loss_percent for m in recent]

        avg_latency = mean(latencies)
        avg_loss = mean(losses)

        latency_score = max(0.0, min(100.0, 120 - (avg_latency * 0.8)))
        loss_penalty = avg_loss * 8
        stability_score = max(0.0, min(100.0, 95 - loss_penalty - (stdev(latencies) if len(latencies) > 1 else 0) * 0.5))

        overall_health = round((latency_score * 0.55 + stability_score * 0.45), 1)
        latency_score = round(latency_score, 1)
        stability_score = round(stability_score, 1)

        if avg_latency < 25 and avg_loss < 0.5:
            classification = "Local-Multicast"
        elif avg_latency < 80 and avg_loss < 2.0:
            classification = "Hyperspace-Stable"
        elif avg_loss < 8.0:
            classification = "Hyperspace-Volatile"
        else:
            classification = "Emerging"

        score = LinkScore(
            peer_id=peer_id,
            overall_health=overall_health,
            latency_score=latency_score,
            stability_score=stability_score,
            confidence=min(0.95, 0.4 + (len(history) * 0.08)),
            classification=classification,
        )
        self._scores[peer_id] = score
        return score

    def _default_score(self, peer_id: str) -> LinkScore:
        return LinkScore(
            peer_id=peer_id,
            overall_health=50.0,
            latency_score=50.0,
            stability_score=50.0,
            confidence=0.2,
            classification="Emerging",
        )

    def get_score(self, peer_id: str) -> LinkScore | None:
        """Return the latest computed score for a peer (or None)."""
        return self._scores.get(peer_id)

    def get_all_scores(self) -> dict[str, LinkScore]:
        return self._scores.copy()

    def demo_run(self, num_peers: int = 5) -> None:
        """Run a self-contained demonstration with simulated hyperspace + local peers.

        Uses Rich for beautiful output when available (pip install -e ".[dev]").
        """
        title = "Nexus Hyperspace — Link Quality Oracle Demo (Prototype v0.1)"

        if RICH_AVAILABLE and self.console:
            self.console.print(Panel.fit(
                f"[bold cyan]{title}[/bold cyan]\n"
                "[dim]Core concepts from ARCHITECTURE.md • M1.1 foundation[/dim]",
                border_style="bright_blue",
                box=box.ROUNDED,
            ))
            self.console.print("[dim]Simulating observations on several peers (local + hyperspace)...[/dim]\n")
        else:
            print(f"\n{title}")
            print("=" * 70)
            print("Simulating observations on several peers (local + hyperspace)...\n")

        demo_peers = [
            "local-cluster-hannover-01",
            "hyperspace-eu-berlin-03",
            "hyperspace-us-west-seattle",
            "hyperspace-asia-tokyo-02",
            "hyperspace-latam-sao-paulo",
        ][:num_peers]

        random.seed(42)

        for peer in demo_peers:
            for _ in range(random.randint(4, 7)):
                if "local" in peer:
                    lat = random.uniform(4, 22)
                    loss = random.uniform(0, 0.4)
                else:
                    lat = random.uniform(45, 165)
                    loss = random.uniform(0.1, 4.5)
                self.record_metrics(peer, latency_ms=lat, packet_loss_percent=loss)

            score = self.get_score(peer)
            if score:
                if RICH_AVAILABLE and self.console:
                    # Will be rendered in table below
                    pass
                else:
                    print(
                        f"{peer:30} | Health: {score.overall_health:5.1f}% | "
                        f"Latency: {score.latency_score:5.1f} | Stability: {score.stability_score:5.1f} | "
                        f"Conf: {score.confidence:.2f} | {score.classification}"
                    )

        if RICH_AVAILABLE and self.console:
            table = Table(
                title="[bold]Link Quality Scores[/bold]",
                show_header=True,
                header_style="bold magenta",
                box=box.ROUNDED,
            )
            table.add_column("Peer", style="cyan", no_wrap=True)
            table.add_column("Health %", justify="right", style="green")
            table.add_column("Latency", justify="right")
            table.add_column("Stability", justify="right")
            table.add_column("Confidence", justify="right")
            table.add_column("Classification", style="yellow")

            for peer in demo_peers:
                score = self.get_score(peer)
                if score:
                    health_style = "green" if score.overall_health > 75 else "yellow" if score.overall_health > 55 else "red"
                    table.add_row(
                        peer,
                        f"[{health_style}]{score.overall_health:.1f}[/{health_style}]",
                        f"{score.latency_score:.1f}",
                        f"{score.stability_score:.1f}",
                        f"{score.confidence:.2f}",
                        score.classification,
                    )

            self.console.print(table)
            self.console.print(
                "[green]✓[/green] Oracle prototype operational. "
                "Scores ready for router / agent consumption.\n"
                "[dim]Next: Real Yggdrasil admin socket + persistent storage (SQLite).[/dim]"
            )
        else:
            print("\n✓ Oracle prototype operational. Scores ready for router / agent consumption.")
            print("Next: Integrate real Yggdrasil admin socket + persistent storage.\n")


if __name__ == "__main__":
    oracle = HyperspaceLinkQualityOracle()
    oracle.demo_run()
