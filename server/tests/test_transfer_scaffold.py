"""Unit tests for the transport-agnostic transfer scaffold — no live SSH."""
import hashlib

import pytest

from rikyu_mcp import transfer


def test_dispatch_unknown_raises(tmp_path):
    with pytest.raises(ValueError):
        transfer.download_file("x", tmp_path / "f", "does_not_exist")


def test_dispatch_noop_verifies(tmp_path, monkeypatch):
    data = b"hello rikyu transfer scaffold\n"
    local_dest = tmp_path / "f"
    local_dest.write_bytes(data)

    expected = hashlib.sha256(data).hexdigest()
    monkeypatch.setattr(transfer, "remote_sha256", lambda path: expected)

    result = transfer.download_file("remote/path", local_dest, transport="_noop")

    assert result.verified is True
    assert result.bytes == len(data)
    assert result.sha256 == expected
    assert result.local_path == str(local_dest)
    assert result.transport == "_noop"
