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
    from .yggdrasil_client import YggdrasilAdminClient
except ImportError:
    from models import LinkMetrics, LinkScore  # type: ignore
    from yggdrasil_client import YggdrasilAdminClient  # type: ignore


class HyperspaceLinkQualityOracle:
    """Core component for recording metrics and computing link health scores.

    Supports both simulated data (for development) and live data from a running
    Yggdrasil node via the admin socket (when available).
    """

    def __init__(self, ewma_alpha: float = 0.3):
        self.ewma_alpha = ewma_alpha
        self._history: dict[str, list[LinkMetrics]] = defaultdict(list)
        self._scores: dict[str, LinkScore] = {}
        self.console = Console() if RICH_AVAILABLE else None
        self.ygg = YggdrasilAdminClient()

    def record_metrics(
        self,
        peer_id: str,
        latency_ms: float,
        packet_loss_percent: float,
        jitter_ms: float = 0.0,
    ) -> LinkScore:
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
        return self._scores.get(peer_id)

    def get_all_scores(self) -> dict[str, LinkScore]:
        return self._scores.copy()

    def poll_from_yggdrasil(self) -> int:
        """Pull current peers from a running Yggdrasil node and record metrics.

        Returns the number of peers successfully recorded.
        This is the bridge from simulation to real-world operation (M1.1/M1.4).
        """
        if not self.ygg.is_available():
            return 0

        try:
            peers = self.ygg.get_peers()
            recorded = 0
            for peer in peers:
                # Yggdrasil peer dict usually contains 'latency', 'bytesSent', 'bytesReceived', etc.
                # For prototype we derive simple loss estimate from activity
                latency = float(peer.get("latency", 0)) / 1_000_000  # ns → ms
                # Very rough loss proxy (in real version we would track over time)
                loss = 0.1 if peer.get("bytesReceived", 0) == 0 else 0.5

                if latency > 0:
                    self.record_metrics(
                        peer_id=peer.get("key", "unknown-peer"),
                        latency_ms=min(latency, 500),
                        packet_loss_percent=loss,
                    )
                    recorded += 1
            return recorded
        except Exception as e:
            if self.console:
                self.console.print(f"[yellow]Warning:[/yellow] Could not poll Yggdrasil: {e}")
            return 0

    def demo_run(self, num_peers: int = 5, prefer_live: bool = True) -> None:
        """Run demonstration.

        If a Yggdrasil admin socket is available and prefer_live=True,
        it will use real peer data. Otherwise falls back to simulation.
        """
        title = "Nexus Hyperspace — Link Quality Oracle Demo (Prototype v0.1)"

        live_count = 0
        if prefer_live:
            live_count = self.poll_from_yggdrasil()

        mode = "LIVE (from Yggdrasil)" if live_count > 0 else "SIMULATED"

        if RICH_AVAILABLE and self.console:
            self.console.print(Panel.fit(
                f"[bold cyan]{title}[/bold cyan]\n"
                f"[dim]Mode: {mode} • M1.1 foundation[/dim]",
                border_style="bright_blue",
                box=box.ROUNDED,
            ))
            if live_count > 0:
                self.console.print(f"[green]✓[/green] Using live data from {live_count} real peers\n")
            else:
                self.console.print("[dim]Simulating observations on several peers (local + hyperspace)...[/dim]\n")
        else:
            print(f"\n{title}")
            print(f"Mode: {mode}")
            print("=" * 70)

        if live_count == 0:
            # Fallback simulation (same peers as before)
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

        # Render results
        peers_to_show = list(self._scores.keys()) if live_count > 0 else [
            "local-cluster-hannover-01",
            "hyperspace-eu-berlin-03",
            "hyperspace-us-west-seattle",
            "hyperspace-asia-tokyo-02",
            "hyperspace-latam-sao-paulo",
        ][:num_peers]

        if RICH_AVAILABLE and self.console:
            table = Table(title="[bold]Link Quality Scores[/bold]", show_header=True, header_style="bold magenta", box=box.ROUNDED)
            table.add_column("Peer", style="cyan", no_wrap=True)
            table.add_column("Health %", justify="right", style="green")
            table.add_column("Latency", justify="right")
            table.add_column("Stability", justify="right")
            table.add_column("Confidence", justify="right")
            table.add_column("Classification", style="yellow")

            for peer in peers_to_show:
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
                "[dim]Next: Persistent storage (SQLite) + full M1.2 classification engine.[/dim]"
            )
        else:
            for peer in peers_to_show:
                score = self.get_score(peer)
                if score:
                    print(f"{peer:30} | Health: {score.overall_health:5.1f}% | Latency: {score.latency_score:5.1f} | Stability: {score.stability_score:5.1f} | {score.classification}")
            print("\n✓ Oracle prototype operational.")


if __name__ == "__main__":
    oracle = HyperspaceLinkQualityOracle()
    oracle.demo_run()
