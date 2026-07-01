"""Unit tests for the scp transport and paramiko-gated sftp registration — no live SSH."""
import importlib.util
from pathlib import Path

import rikyu_mcp.transfer
from rikyu_mcp.transports.t_scp_sftp import _scp_argv


def test_scp_registered():
    assert "scp" in rikyu_mcp.transfer._TRANSPORTS


def test_scp_argv():
    assert _scp_argv("rikyu", "logs/a.out", Path("/tmp/a.out")) == [
        "scp",
        "-p",
        "rikyu:logs/a.out",
        "/tmp/a.out",
    ]


def test_sftp_registration_matches_paramiko_availability():
    has_paramiko = importlib.util.find_spec("paramiko") is not None
    assert ("sftp" in rikyu_mcp.transfer._TRANSPORTS) == has_paramiko
