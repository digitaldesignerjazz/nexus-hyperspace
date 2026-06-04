"""Lightweight client for the Yggdrasil admin API (Unix domain socket).

Used by the Link Quality Oracle to fetch real peer metrics instead of simulation.
This is the foundation for M1.1 / M1.4 integration with live Yggdrasil nodes.

Yggdrasil admin socket is usually at one of:
  - /var/run/yggdrasil/yggdrasil.sock
  - ~/.yggdrasil/yggdrasil.sock
  - or the path configured in yggdrasil.conf under "AdminListen"

The protocol is length-prefixed JSON (big-endian uint32 length + JSON).
"""

from __future__ import annotations

import json
import socket
import struct
from pathlib import Path
from typing import Any


class YggdrasilAdminClient:
    """Minimal client for Yggdrasil admin socket."""

    DEFAULT_SOCKET_PATHS = [
        "/var/run/yggdrasil/yggdrasil.sock",
        str(Path.home() / ".yggdrasil" / "yggdrasil.sock"),
        "/run/yggdrasil/yggdrasil.sock",
    ]

    def __init__(self, socket_path: str | None = None):
        self.socket_path = socket_path or self._find_socket()
        self._connected = False

    def _find_socket(self) -> str | None:
        for path in self.DEFAULT_SOCKET_PATHS:
            if Path(path).exists():
                return path
        return None

    def is_available(self) -> bool:
        return self.socket_path is not None and Path(self.socket_path).exists()

    def _send_request(self, method: str, **params: Any) -> dict[str, Any]:
        if not self.socket_path:
            raise ConnectionError("No Yggdrasil admin socket found")

        request = {
            "request": method,
            "arguments": params,
        }
        data = json.dumps(request).encode("utf-8")
        length = struct.pack(">I", len(data))  # big-endian uint32

        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.connect(self.socket_path)
            sock.sendall(length + data)

            # Read response length
            resp_len_data = sock.recv(4)
            if len(resp_len_data) != 4:
                raise ConnectionError("Invalid response from Yggdrasil admin socket")
            resp_len = struct.unpack(">I", resp_len_data)[0]

            # Read response body
            response_data = b""
            while len(response_data) < resp_len:
                chunk = sock.recv(resp_len - len(response_data))
                if not chunk:
                    break
                response_data += chunk

        response = json.loads(response_data.decode("utf-8"))
        if "error" in response and response["error"]:
            raise RuntimeError(f"Yggdrasil admin error: {response['error']}")
        return response.get("response", {})

    def get_self(self) -> dict[str, Any]:
        """Return information about this node."""
        return self._send_request("getSelf")

    def get_peers(self) -> list[dict[str, Any]]:
        """Return list of connected peers with their current state."""
        resp = self._send_request("getPeers")
        # The response is usually a dict with peer pubkeys as keys
        if isinstance(resp, dict):
            return list(resp.values())
        return resp if isinstance(resp, list) else []

    def get_tree(self) -> dict[str, Any]:
        """Return the current spanning tree / routing information."""
        return self._send_request("getTree")

    def get_dht(self) -> dict[str, Any]:
        """Return DHT information."""
        return self._send_request("getDHT")
