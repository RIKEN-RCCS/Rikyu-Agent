"""Offline tests for the direct-ssh exec+checksum helpers in transfer.py."""
from rikyu_mcp import transfer


def test_ssh_argv():
    assert transfer._ssh_argv("ai4s-r2", "sha256sum 'f'") == [
        "ssh", "-o", "BatchMode=yes", "ai4s-r2", "cd $HOME && sha256sum 'f'",
    ]


def test_remote_sha256_parses_first_field(monkeypatch):
    monkeypatch.setattr(transfer, "_ssh_capture", lambda cmd: "abc123  somefile\n")
    assert transfer.remote_sha256("x") == "abc123"


def test_run_capture_delegates(monkeypatch):
    seen = {}

    def fake(cmd):
        seen["cmd"] = cmd
        return "SENTINEL"

    monkeypatch.setattr(transfer, "_ssh_capture", fake)
    assert transfer.run_capture("echo hi") == "SENTINEL"
    assert seen["cmd"] == "echo hi"
