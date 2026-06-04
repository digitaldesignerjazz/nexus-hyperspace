"""Basic CLI tests for nexus_hyperspace.oracle module."""

import subprocess
import sys


def test_cli_help_runs():
    result = subprocess.run(
        [sys.executable, "-m", "nexus_hyperspace.oracle", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "--history" in result.stdout or "--status" in result.stdout


def test_cli_status_runs_without_crash():
    # Should not crash even with no data
    result = subprocess.run(
        [sys.executable, "-m", "nexus_hyperspace.oracle", "--status"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
