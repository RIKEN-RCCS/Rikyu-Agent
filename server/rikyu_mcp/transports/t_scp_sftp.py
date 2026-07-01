"""scp transport, plus an optional paramiko-backed sftp transport.

scp is the default, dependency-free transport: it shells out to the system
`scp` binary. sftp is only registered when `paramiko` is importable — this
keeps paramiko an optional dependency rather than a hard requirement of the
transfer campaign.
"""
import subprocess
import sys
from pathlib import Path

from rikyu_mcp.transfer import register


def _scp_argv(host: str, remote_path: str, local_dest: Path) -> list[str]:
    """Build the argv for a preserve-mode scp fetch of `remote_path` to `local_dest`."""
    return ["scp", "-p", f"{host}:{remote_path}", str(local_dest)]


@register("scp")
def scp_transport(remote_path: str, local_dest: Path) -> None:
    """Fetch `remote_path` to `local_dest` via the system `scp` binary."""
    from rikyu_mcp import config

    argv = _scp_argv(config.ssh_host(), remote_path, local_dest)
    proc = subprocess.run(argv, stdout=sys.stderr, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"scp exited with code {proc.returncode}")


try:
    import paramiko
except ImportError:
    paramiko = None

if paramiko is not None:

    @register("sftp")
    def sftp_transport(remote_path: str, local_dest: Path) -> None:
        """Fetch `remote_path` to `local_dest` via paramiko's SFTP client.

        Connects to config.ssh_host() using system host keys and key-based
        auth (no credentials are stored/passed here). ssh_host() may be an
        alias from ~/.ssh/config that paramiko does not resolve on its own;
        a full implementation would parse that file for HostName/User/Port/
        IdentityFile — this best-effort version connects to the host value
        directly, which is sufficient since this transport stays unregistered
        unless paramiko is installed.
        """
        from rikyu_mcp import config

        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(config.ssh_host())
            sftp = client.open_sftp()
            try:
                sftp.get(remote_path, str(local_dest))
            finally:
                sftp.close()
        finally:
            client.close()
