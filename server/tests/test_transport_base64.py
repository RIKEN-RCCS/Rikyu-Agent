"""Unit tests for the base64 download transport — no live SSH."""
import base64

import rikyu_mcp.transfer
from rikyu_mcp.transports.t_base64 import _decode


def test_base64_registered():
    rikyu_mcp.transfer._ensure_transports_loaded()
    assert "base64" in rikyu_mcp.transfer._TRANSPORTS


def test_decode_roundtrip():
    data = b"hello\x00\xff"
    assert _decode(base64.b64encode(data).decode()) == data
