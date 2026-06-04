"""Hyperspace Link Quality Oracle (M1.1)

Real-time and historical scoring of Yggdrasil hyperspace (and local) peer links.
Provides trusted signals for the Nexus agent router and constellation manager.

This is an early prototype implementing core concepts from ARCHITECTURE.md.
"""

from __future__ import annotations

import argparse
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
    from .storage import OracleStorage
    from .peer_classifier import classify_peer
except ImportError:
    from models import LinkMetrics, LinkScore
    from yggdrasil_client import YggdrasilAdminClient
    from storage import OracleStorage
    from peer_classifier import classify_peer


class HyperspaceLinkQualityOracle:
    """Core component for recording metrics and computing link health scores.

    Supports live Yggdrasil data with improved delta-based loss/jitter calculation,
    SQLite persistence, and integration with the PeerClassifier (M1.2).
    """

    def __init__(self, ewma_alpha: float = 0.3, persist: bool = True):
        self.ewma_alpha = ewma_alpha
        self._history: dict[str, list[LinkMetrics]] = defaultdict(list)
        self._scores: dict[str, LinkScore] = {}
        self.console = Console() if RICH_AVAILABLE else None
        self.ygg = YggdrasilAdminClient()
        self.storage = OracleStorage() if persist else None
        self._last_bytes: dict[str, dict] = defaultdict(dict)

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

        if self.storage:
            self.storage.record_metric(peer_id, latency_ms, packet_loss_percent, jitter_ms)

        score = self._recalculate_score(peer_id)

        classify_peer(
            peer_id=peer_id,
            current_score=score,
            recent_latencies=[m.latency_ms for m in self._history[peer_id][-8:]],
            recent_losses=[m.packet_loss_percent for m in self._history[peer_id][-8:]],
        )
        return score

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

        if self.storage:
            self.storage.save_score(
                peer_id, overall_health, latency_score, stability_score,
                score.confidence, classification
            )

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
        if not self.ygg.is_available():
            return 0

        try:
            peers = self.ygg.get_peers()
            recorded = 0
            now = time.time()

            for peer in peers:
                key = peer.get("key", "unknown")
                curr_bytes_sent = peer.get("bytesSent", 0)
                curr_bytes_recv = peer.get("bytesReceived", 0)
                latency_ns = peer.get("latency", 0)

                latency_ms = latency_ns / 1_000_000 if latency_ns > 0 else 50.0

                prev = self._last_bytes.get(key, {})
                loss = 0.5
                jitter = 0.0

                if prev:
                    time_delta = max(1, now - prev.get("ts", now - 30))
                    sent_delta = max(0, curr_bytes_sent - prev.get("sent", 0))
                    recv_delta = max(0, curr_bytes_recv - prev.get("recv", 0))

                    if sent_delta > 1000:
                        ratio = recv_delta / max(sent_delta, 1)
                        loss = max(0.0, min(15.0, (1.0 - ratio) * 12))

                    if key in self._history and len(self._history[key]) >= 2:
                        recent_lat = [m.latency_ms for m in self._history[key][-5:]]
                        if len(recent_lat) >= 2:
                            jitter = stdev(recent_lat)

                self._last_bytes[key] = {
                    "sent": curr_bytes_sent,
                    "recv": curr_bytes_recv,
                    "ts": now,
                }

                self.record_metrics(
                    peer_id=key,
                    latency_ms=min(latency_ms, 600),
                    packet_loss_percent=round(loss, 2),
                    jitter_ms=round(jitter, 1),
                )
                recorded += 1

            return recorded
        except Exception as e:
            if self.console:
                self.console.print(f"[yellow]Warning:[/yellow] Could not poll Yggdrasil: {e}")
            return 0

    def show_history(self, peer_id: str, limit: int = 10):
        """Print recent metrics and latest score for a specific peer."""
        if not self.storage:
            print("Persistence is disabled.")
            return

        metrics = self.storage.get_recent_metrics(peer_id, limit)
        score = self.get_score(peer_id)

        if RICH_AVAILABLE and self.console:
            self.console.print(Panel.fit(f"[bold]History for {peer_id}[/bold]", border_style="cyan"))
            if metrics:
                table = Table(show_header=True, header_style="bold")
                table.add_column("Time")
                table.add_column("Latency (ms)", justify="right")
                table.add_column("Loss %", justify="right")
                table.add_column("Jitter (ms)", justify="right")

                for m in reversed(metrics):
                    ts = time.strftime("%H:%M:%S", time.localtime(m[3]))
                    table.add_row(ts, f"{m[0]:.1f}", f"{m[1]:.2f}", f"{m[2]:.1f}")
                self.console.print(table)
            else:
                self.console.print("[dim]No historical data found for this peer.[/dim]")

            if score:
                self.console.print(f"\nLatest score: [bold]{score.overall_health:.1f}%[/bold] health | {score.classification}")
        else:
            print(f"\nHistory for {peer_id}:")
            for m in reversed(metrics):
                print(f"  {time.strftime('%H:%M:%S', time.localtime(m[3]))} | Latency: {m[0]:.1f}ms | Loss: {m[1]:.2f}% | Jitter: {m[2]:.1f}ms")
            if score:
                print(f"Latest: {score.overall_health:.1f}% health | {score.classification}")

    def demo_run(self, num_peers: int = 5, prefer_live: bool = True) -> None:
        title = "Nexus Hyperspace — Link Quality Oracle Demo (Prototype v0.1)"

        live_count = 0
        if prefer_live:
            live_count = self.poll_from_yggdrasil()

        mode = "LIVE (from Yggdrasil)" if live_count > 0 else "SIMULATED + PERSISTENT"

        if RICH_AVAILABLE and self.console:
            self.console.print(Panel.fit(
                f"[bold cyan]{title}[/bold cyan]\n"
                f"[dim]Mode: {mode} • M1.1 + M1.2[/dim]",
                border_style="bright_blue",
                box=box.ROUNDED,
            ))
            if live_count > 0:
                self.console.print(f"[green]✓[/green] Using live data from {live_count} real peers (improved delta metrics)\n")
            else:
                self.console.print("[dim]Simulating observations + persisting to SQLite...[/dim]\n")
        else:
            print(f"\n{title}")
            print(f"Mode: {mode}")
            print("=" * 70)

        if live_count == 0:
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
            table.add_column("Jitter", justify="right")
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
                        f"{getattr(score, 'jitter_ms', 0):.1f}",
                        score.classification,
                    )
            self.console.print(table)
            self.console.print(
                "[green]✓[/green] Oracle prototype operational (M1.1 + M1.2). "
                "Data persisted to data/oracle.db\n"
                "[dim]Use --history <peer> to query stored data.[/dim]"
            )
        else:
            for peer in peers_to_show:
                score = self.get_score(peer)
                if score:
                    print(f"{peer:30} | Health: {score.overall_health:5.1f}% | Latency: {score.latency_score:5.1f} | Stability: {score.stability_score:5.1f} | {score.classification}")
            print("\n✓ Oracle prototype operational. Data saved to data/oracle.db")


def main():
    parser = argparse.ArgumentParser(description="Nexus Hyperspace Link Quality Oracle")
    parser.add_argument("--history", metavar="PEER_ID", help="Show recent history for a specific peer")
    parser.add_argument("--no-live", action="store_true", help="Force simulation mode even if Yggdrasil is available")
    parser.add_argument("--peers", type=int, default=5, help="Number of simulated peers (when not live)")

    args = parser.parse_args()

    oracle = HyperspaceLinkQualityOracle()

    if args.history:
        oracle.show_history(args.history)
    else:
        oracle.demo_run(num_peers=args.peers, prefer_live=not args.no_live)


if __name__ == "__main__":
    main()
