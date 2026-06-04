"""Tests for YggdrasilAdminClient using a mock socket."""

import socket
import struct
import json
from unittest.mock import patch, MagicMock

import pytest

from nexus_hyperspace.yggdrasil_client import YggdrasilAdminClient


def test_yggdrasil_client_is_available_false_when_no_socket():
    client = YggdrasilAdminClient(socket_path="/nonexistent/path.sock")
    assert client.is_available() is False


def test_yggdrasil_client_get_peers_mocked():
    # Simulate Yggdrasil admin socket response
    mock_response = {
        "response": {
            "peer1": {"key": "peer1", "latency": 45000000, "bytesSent": 12345, "bytesReceived": 12000},
            "peer2": {"key": "peer2", "latency": 120000000, "bytesSent": 5000, "bytesReceived": 4800},
        }
    }
    mock_data = json.dumps(mock_response).encode("utf-8")
    mock_len = struct.pack(">I", len(mock_data))

    with patch("socket.socket") as mock_socket:
        instance = mock_socket.return_value.__enter__.return_value
        instance.recv.side_effect = [mock_len, mock_data]

        client = YggdrasilAdminClient(socket_path="/fake.sock")
        peers = client.get_peers()

        assert len(peers) == 2
        assert peers[0]["key"] == "peer1"
        assert peers[1]["key"] == "peer2"
