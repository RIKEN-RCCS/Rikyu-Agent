"""Transport-agnostic file transfer core.

This module holds the pluggable skeleton shared by every download transport
(scp, sftp, base64-over-ssh, rsync, ...). Each transport is added later via
``@register("name")`` on a function that knows how to land bytes at a local
destination; this module itself never picks a transport and does not depend on
the local-path *policy* in ``config`` (download_dir/resolve_local_dest) —
callers resolve destination paths and the transport choice before reaching
here. It does read ``config.ssh_host()`` (lazily) to know which host to ssh to.
"""
import hashlib
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from rikyu_mcp.middleware import quote_path

# Streamed read size for local checksumming.
_CHUNK_BYTES = 1024 * 1024


@dataclass
class TransferResult:
    """Outcome of a single download, independent of which transport ran it."""

    local_path: str
    bytes: int
    sha256: str
    verified: bool
    transport: str


_TRANSPORTS: dict[str, "Callable[[str, Path], None]"] = {}
_discovered = False


def _ensure_transports_loaded() -> None:
    """Import every module in rikyu_mcp.transports so their @register calls run.

    Done lazily (not at import time) to avoid a circular import: transport
    modules import `register`/`run_capture` from this module.
    """
    global _discovered
    if _discovered:
        return
    import importlib
    import pkgutil

    from rikyu_mcp import transports

    for mod in pkgutil.iter_modules(transports.__path__):
        importlib.import_module(f"rikyu_mcp.transports.{mod.name}")
    _discovered = True


def register(name: str) -> Callable[[Callable[[str, Path], None]], Callable[[str, Path], None]]:
    """Decorator registering a transport under `name` in `_TRANSPORTS`.

    A transport has signature ``fn(remote_path: str, local_dest: Path) -> None``
    and is responsible for landing the file's bytes at `local_dest`.
    """

    def decorator(fn: Callable[[str, Path], None]) -> Callable[[str, Path], None]:
        _TRANSPORTS[name] = fn
        return fn

    return decorator


def download_file(remote_path: str, local_dest: Path, transport: str) -> TransferResult:
    """Fetch `remote_path` to `local_dest` via the named transport, verifying checksum.

    Computes the expected SHA-256 on the remote side before transferring,
    invokes the transport to land the bytes, then checksums the local copy
    and reports whether the two match.
    """
    _ensure_transports_loaded()
    try:
        fn = _TRANSPORTS[transport]
    except KeyError:
        raise ValueError(
            f"unknown transport {transport!r}; known: {sorted(_TRANSPORTS)}"
        ) from None

    expected = remote_sha256(remote_path)
    fn(remote_path, local_dest)
    actual = local_sha256(local_dest)

    return TransferResult(
        local_path=str(local_dest),
        bytes=local_dest.stat().st_size,
        sha256=actual,
        verified=(expected == actual),
        transport=transport,
    )


def _ssh_argv(host: str, cmd: str) -> list[str]:
    """Argv for running `cmd` on `host` over a batch-mode ssh, home-relative."""
    return ["ssh", "-o", "BatchMode=yes", host, f"cd $HOME && {cmd}"]


def _ssh_capture(cmd: str) -> str:
    """Run `cmd` on the login node over a direct ssh subprocess; return stdout.

    Bypasses remotemanager entirely: remotemanager builds an rsync transport
    and version-checks it (>=3.0) at Computer construction, which fails on
    hosts with older/BSD rsync (e.g. macOS openrsync) even for a plain command.
    A direct ssh subprocess needs only OpenSSH, which is universal.
    """
    from rikyu_mcp import config

    proc = subprocess.run(
        _ssh_argv(config.ssh_host(), cmd),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"ssh exited {proc.returncode}")
    return proc.stdout


def remote_sha256(path: str) -> str:
    """SHA-256 of a file on the login node, via `sha256sum`."""
    return _ssh_capture(f"sha256sum {quote_path(path)}").split()[0]


def local_sha256(path: Path) -> str:
    """SHA-256 of a local file, streamed in fixed-size chunks."""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        while chunk := fh.read(_CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def run_capture(cmd: str) -> str:
    """Run a login-node command over direct ssh, returning the FULL stdout.

    Two reasons this exists rather than reusing middleware.run_command:
    - it does NOT truncate output at OUTPUT_LIMIT_BYTES — that 200 KB cap is
      the very bug this transfer campaign exists to fix (it silently corrupts
      base64 bodies of files larger than ~146 KB);
    - it avoids remotemanager's rsync>=3.0 version gate, so transports like
      base64 work even where a modern rsync is not on PATH.
    """
    return _ssh_capture(cmd)


@register("_noop")
def _noop_transport(remote_path: str, local_dest: Path) -> None:
    """Test-only transport: assumes `local_dest` is already populated.

    Real transports fetch bytes from `remote_path` to `local_dest`; this one
    does nothing, so tests can pre-write `local_dest` themselves and exercise
    `download_file`'s checksum/verify plumbing without any SSH.
    """
