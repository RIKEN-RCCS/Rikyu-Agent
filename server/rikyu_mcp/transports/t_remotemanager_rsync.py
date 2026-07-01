"""Download transport backed by remotemanager's checksummed rsync.

Reuses the server's existing cached SSH target (``get_frontend()``, a
``Computer``/``URL`` subclass already wired to the login host) and hands it
to remotemanager's ``rsync`` Transport, which shells out to the local
``rsync`` binary with ``--checksum`` to pull a single file. rsync always
lands the file under its remote basename inside the local destination
directory, so if the caller asked for a different local filename we rename
it into place after the transfer.
"""
import contextlib
import os
import sys
from pathlib import Path

from remotemanager.transport import rsync

from rikyu_mcp.middleware import get_frontend
from rikyu_mcp.transfer import register


@register("rm_rsync")
def rm_rsync_transport(remote_path: str, local_dest: Path) -> None:
    """Pull `remote_path` from the login node to `local_dest` via rsync."""
    t = rsync(url=get_frontend())
    t.queue_for_pull(
        files=os.path.basename(remote_path),
        local=str(local_dest.parent),
        remote=(os.path.dirname(remote_path) or "."),
    )
    # rsync (and remotemanager) may print progress to stdout, which would
    # corrupt the MCP stdio transport — divert anything emitted.
    #
    # NB: do NOT use raise_errors=True. remotemanager treats *any* stderr as a
    # failure, but this cluster's SSH server prints a post-quantum warning
    # banner to stderr on every connection ("** WARNING: connection is not
    # using a post-quantum key exchange ..."), which would spuriously fail an
    # otherwise-successful (rc 0) transfer. Judge success by the rsync exit
    # code instead; download_file's checksum is the ultimate integrity gate.
    with contextlib.redirect_stdout(sys.stderr):
        results = t.transfer(raise_errors=False)
    failed = [c for c in (results if isinstance(results, list) else [results])
              if c.returncode != 0]
    if failed:
        raise RuntimeError(failed[0].stderr.strip()
                           or f"rsync exited {failed[0].returncode}")

    landed = local_dest.parent / os.path.basename(remote_path)
    if landed != local_dest:
        landed.rename(local_dest)
