"""Transport-agnostic file transfer core.

This module holds the pluggable skeleton shared by every download transport
(scp, sftp, base64-over-ssh, rsync, ...). Each transport is added later via
``@register("name")`` on a function that knows how to land bytes at a local
destination; this module itself never picks a transport and never imports
``config`` — callers resolve paths and transport choice before reaching here.
"""
import contextlib
import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from rikyu_mcp.middleware import get_frontend, quote_path, run_command

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


def remote_sha256(path: str) -> str:
    """SHA-256 of a file on the login node, via `sha256sum`."""
    output = run_command(f"sha256sum {quote_path(path)}")
    return output.split()[0]


def local_sha256(path: Path) -> str:
    """SHA-256 of a local file, streamed in fixed-size chunks."""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        while chunk := fh.read(_CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def run_capture(cmd: str) -> str:
    """Run a login-node command via get_frontend().cmd(...), returning full stdout.

    Unlike middleware.run_command, this does NOT truncate output at
    OUTPUT_LIMIT_BYTES — that 200 KB cap is the very bug this transfer
    campaign exists to fix. Transports that need raw, complete stdout (e.g.
    base64-encoded file bodies) should call this instead.
    """
    with contextlib.redirect_stdout(sys.stderr):
        result = get_frontend().cmd(cmd, raise_errors=False)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(detail or f"command exited with code {result.returncode}")
    return result.stdout or ""


@register("_noop")
def _noop_transport(remote_path: str, local_dest: Path) -> None:
    """Test-only transport: assumes `local_dest` is already populated.

    Real transports fetch bytes from `remote_path` to `local_dest`; this one
    does nothing, so tests can pre-write `local_dest` themselves and exercise
    `download_file`'s checksum/verify plumbing without any SSH.
    """
