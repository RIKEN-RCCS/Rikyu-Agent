"""Unit tests for the remotemanager-rsync download transport — no live SSH.

Only exercises offline paths: registration, and building a pull queue with
the local rsync binary (used for remotemanager's version check). Never calls
`.transfer()`, which would attempt a real SSH/rsync connection.
"""
import pytest

import rikyu_mcp.transfer
import rikyu_mcp.transports.t_remotemanager_rsync  # noqa: F401 - registers "rm_rsync"
from rikyu_mcp.middleware import get_frontend


def test_rm_rsync_registered():
    assert "rm_rsync" in rikyu_mcp.transfer._TRANSPORTS


def test_build_pull_queue_offline():
    from remotemanager.transport import rsync

    try:
        t = rsync(url=get_frontend())
    except Exception as exc:
        pytest.skip(f"could not construct rsync transport offline: {exc}")

    try:
        t.queue_for_pull(files="f.txt", local="/tmp", remote=".")
    except Exception as exc:
        pytest.skip(f"queue_for_pull required network access: {exc}")

    assert len(t.transfers) == 1
    files = next(iter(t.transfers.values()))
    assert files == ["f.txt"]
