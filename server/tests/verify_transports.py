"""Live transport conformance check: round-trip a real fixture through every transport.

Tier gate before benchmarking (see __roadmap__/fs-download-rework/transports/
benchmark/verify_transports.md): proves each registered transport actually
pulls a real file from the cluster with a matching checksum, distinguishing
"broken" (FAIL) from "can't run here" (SKIP) so a missing local binary or an
old rsync doesn't masquerade as a transport bug.

Usage:  cd server && uv run python tests/verify_transports.py
"""
import argparse
import os
import sys
import tempfile
from pathlib import Path

from rikyu_mcp import config, transfer
from rikyu_mcp.middleware import quote_path

FIXTURE_PREFIX = "rikyu-verify-transports"


def make_remote_fixture(host: str, size: int = 65536) -> str:
    """Create one random `size`-byte file on `host` via a single ssh call; return its path.

    Uses /dev/urandom + head so the fixture is created with a single
    BatchMode ssh round trip, no local temp file involved.
    """
    remote_path = f"$HOME/.cache/{FIXTURE_PREFIX}-{os.getpid()}"
    cmd = f"mkdir -p $(dirname {remote_path}) && head -c {size} /dev/urandom > {remote_path} && echo {remote_path}"
    proc_argv = ["ssh", "-o", "BatchMode=yes", host, cmd]
    import subprocess

    proc = subprocess.run(proc_argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"ssh exited {proc.returncode}")
    return proc.stdout.strip()


def cleanup_remote_fixture(host: str, remote_path: str) -> None:
    """Best-effort removal of a fixture created by `make_remote_fixture`."""
    import subprocess

    subprocess.run(
        ["ssh", "-o", "BatchMode=yes", host, f"rm -f {quote_path(remote_path)}"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )


def verify_one(name: str, remote_path: str, host: str) -> str:
    """Round-trip `remote_path` through transport `name`; return 'OK', 'SKIP(reason)', or 'FAIL(reason)'.

    A remotemanager rsync-version RuntimeError or a missing-binary
    FileNotFoundError means the environment can't run this transport here —
    SKIP, not FAIL. A verified=False result or any other unexpected error is
    a genuine FAIL.
    """
    with tempfile.TemporaryDirectory(prefix=FIXTURE_PREFIX) as tmp_dir:
        local_dest = Path(tmp_dir) / "fixture"
        try:
            result = transfer.download_file(remote_path, local_dest, name)
        except FileNotFoundError as exc:
            return f"SKIP({exc})"
        except RuntimeError as exc:
            if "rsync version" in str(exc):
                return f"SKIP({exc})"
            return f"FAIL({exc})"
        except Exception as exc:  # noqa: BLE001 - surfaced as a genuine FAIL
            return f"FAIL({exc})"

        if not result.verified:
            return "FAIL(checksum mismatch)"
        return "OK"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Round-trip a real fixture through every registered transport.",
    )
    parser.add_argument(
        "--size", type=int, default=65536,
        help="Fixture size in bytes (default: 65536).",
    )
    args = parser.parse_args()

    host = config.ssh_host()
    transfer._ensure_transports_loaded()
    names = sorted(n for n in transfer._TRANSPORTS if n != "_noop")

    remote_path = None
    had_failure = False
    try:
        remote_path = make_remote_fixture(host, size=args.size)
        for name in names:
            outcome = verify_one(name, remote_path, host)
            print(f"{name}: {outcome}")
            if outcome.startswith("FAIL"):
                had_failure = True
    finally:
        if remote_path is not None:
            cleanup_remote_fixture(host, remote_path)

    return 1 if had_failure else 0


if __name__ == "__main__":
    sys.exit(main())
