"""Portability probe: fingerprint the rsync/scp/ssh tooling on both ends.

Local `rsync` on macOS is frequently BSD/openrsync (protocol-compatible but
version-gated out by remotemanager's `rsync` Transport, which requires >=3.0)
shadowing a newer Homebrew GNU rsync later in PATH. This script records,
for the local machine and (optionally) a remote host, which rsync/scp/ssh
binaries exist, how they classify, and whether remotemanager's `Computer`
construction succeeds under the *current* PATH — durable evidence for the
benchmark report and for porting to new clusters (banyan, dgx1, ...).

Usage:  cd server && uv run python tests/probe_portability.py [--host <alias>]
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

# server/tests/probe_portability.py -> tests -> server -> repo root
_REPO_ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = _REPO_ROOT / "__reports__" / "fs-download-rework" / "portability.json"


def _run(argv: list[str]) -> tuple[int, str]:
    """Run `argv`, returning (returncode, combined stdout+stderr).

    Never raises on a non-zero exit or a missing binary: tools like BSD
    `scp` reject `-V` and print usage to stderr with exit code 1, and that
    is itself a meaningful, reportable result rather than a probe failure.
    """
    try:
        proc = subprocess.run(
            argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, timeout=10,
        )
        return proc.returncode, proc.stdout.strip()
    except FileNotFoundError as exc:
        return -1, str(exc)
    except subprocess.TimeoutExpired:
        return -1, "timed out"


def classify_rsync(version_output: str) -> str:
    """Classify an `rsync --version` transcript as "openrsync", "GNU", or "unknown".

    openrsync (the BSD rsync shipped as macOS's /usr/bin/rsync) prints its
    own name on the first line; GNU rsync's banner starts with "rsync
    version". Anything else is reported as "unknown" rather than guessed at.
    """
    lowered = version_output.lower()
    if "openrsync" in lowered:
        return "openrsync"
    if "rsync  version" in lowered or "rsync version" in lowered:
        return "GNU"
    return "unknown"


def _which_all(name: str) -> list[str]:
    """Every `name` on PATH, in PATH order (first entry is what actually runs)."""
    code, out = _run(["which", "-a", name])
    if code != 0 or not out:
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def _probe_binary(name: str) -> dict:
    """PATH resolution + version info for one local binary (`rsync`/`scp`/`ssh`)."""
    resolved = shutil.which(name)
    all_paths = _which_all(name)
    entries = []
    for path in all_paths:
        version_flag = "-V" if name in ("scp", "ssh") else "--version"
        _, output = _run([path, version_flag])
        entry = {"path": path, "version_output": output}
        if name == "rsync":
            entry["flavor"] = classify_rsync(output)
        entries.append(entry)
    return {
        "resolved": resolved,
        "shadowed": len(all_paths) > 1,
        "path_order": entries,
    }


def probe_local() -> dict:
    """Fingerprint local rsync/scp/ssh and whether remotemanager's Computer builds.

    Purely local: no network access, no ssh round trip. Safe to call
    unconditionally, including offline.
    """
    report = {
        "rsync": _probe_binary("rsync"),
        "scp": _probe_binary("scp"),
        "ssh": _probe_binary("ssh"),
    }

    try:
        from remotemanager import Computer

        Computer(template="#!/bin/bash -l", host="localhost",
                  submitter="bash", python="python3")
        report["remotemanager_computer"] = {"ok": True, "message": None}
    except Exception as exc:  # noqa: BLE001 - reporting, not handling
        report["remotemanager_computer"] = {"ok": False, "message": str(exc)}

    return report


def probe_remote(host: str) -> dict:
    """Fingerprint rsync/scp/uname on `host` in a single ssh round trip.

    Runs `rsync --version; scp -V 2>&1 | head -1; uname -a` once over a
    batch-mode ssh, mirroring the ssh invocation transfer.py uses elsewhere
    in this codebase (no remotemanager involved, so a pre-3.0 local/remote
    rsync cannot block the probe itself).
    """
    remote_cmd = "rsync --version; scp -V 2>&1 | head -1; uname -a"
    argv = ["ssh", "-o", "BatchMode=yes", host, remote_cmd]
    code, output = _run(argv)
    return {
        "host": host,
        "ok": code == 0,
        "returncode": code,
        "raw_output": output,
    }


def main() -> None:
    from rikyu_mcp import config

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=config.ssh_host(),
                        help="SSH alias/host to probe (default: config.ssh_host())")
    args = parser.parse_args()

    report = {
        "local": probe_local(),
        "remote": probe_remote(args.host),
    }

    print(json.dumps(report, indent=2))

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n")
    print(f"\nwrote {REPORT_PATH}", file=sys.stderr)


if __name__ == "__main__":
    main()
