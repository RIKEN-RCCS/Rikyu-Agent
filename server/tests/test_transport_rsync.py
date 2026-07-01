"""Offline tests for the direct rsync subprocess transport.

No real transfer happens here: we only check that the transport registers
itself under "rsync" and that the argv it builds is exactly what we expect
rsync to be invoked with.
"""
from pathlib import Path

import rikyu_mcp.transfer
from rikyu_mcp.transports import t_rsync_subprocess
from rikyu_mcp.transports.t_rsync_subprocess import _rsync_argv


def test_rsync_registered():
    assert "rsync" in rikyu_mcp.transfer._TRANSPORTS


def test_rsync_argv():
    assert _rsync_argv("rikyu", "data/f.bin", Path("/tmp/f.bin")) == [
        "rsync",
        "-az",
        "--checksum",
        "--partial",
        "rikyu:data/f.bin",
        "/tmp/f.bin",
    ]
