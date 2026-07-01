"""Direct rsync download transport.

Shells out to the local ``rsync`` binary over SSH to fetch a remote file,
rather than routing bytes through the MCP frontend's command channel. This
lets large or resumable transfers stream directly between the two
filesystems instead of being buffered through stdout capture.
"""
import subprocess
import sys
from pathlib import Path

from rikyu_mcp.transfer import register


def _rsync_argv(host: str, remote_path: str, local_dest: Path) -> list[str]:
    """Build the rsync argv for pulling `remote_path` on `host` to `local_dest`.

    -a preserves permissions/times/links, -z compresses in transit,
    --checksum verifies content (not just size/mtime), --partial keeps
    partially-transferred files so interrupted downloads can resume.
    """
    return [
        "rsync",
        "-az",
        "--checksum",
        "--partial",
        f"{host}:{remote_path}",
        str(local_dest),
    ]


@register("rsync")
def rsync_transport(remote_path: str, local_dest: Path) -> None:
    """Fetch `remote_path` to `local_dest` via a direct rsync subprocess.

    stdout is redirected to stderr so rsync's progress output never corrupts
    the MCP server's stdio transport; stderr is captured so failures can be
    surfaced in the raised error.
    """
    from rikyu_mcp import config

    argv = _rsync_argv(config.ssh_host(), remote_path, local_dest)
    proc = subprocess.run(argv, stdout=sys.stderr, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"rsync exited {proc.returncode}")
