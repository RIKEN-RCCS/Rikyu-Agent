"""Remote-execution layer: all cluster interaction funnels through here.

Built on remotemanager's Computer.cmd (a direct SSH exec, ~0.6s per call).
Three conventions are enforced in one place:

- Commands run under a login shell (Slurm on AI4S resolves its configuration
  through the login environment; a bare non-login shell cannot find it).
- The working directory is the user's home, so relative paths behave the way
  users expect.
- Commands and file contents travel base64-encoded, so arbitrary quoting
  survives the SSH layer intact.
"""
import base64
import contextlib
import shlex
import sys
from functools import lru_cache


def norm_path(path: str) -> str:
    """Strip a leading ~ so remote paths resolve under the home directory.

    run_command sets CWD to $HOME, so relative paths already resolve there.
    shlex.quote wraps in single quotes which suppresses tilde expansion, so
    ~/foo must become foo before quoting; bare ~ becomes '.'.
    """
    if path == "~":
        return "."
    if path.startswith("~/"):
        return path[2:]
    return path


def quote_path(path: str) -> str:
    """shlex.quote a remote path after normalizing a leading ~."""
    return shlex.quote(norm_path(path))

from remotemanager import Computer

from rikyu_mcp import config

# Cap what a single call can pour into the MCP context.
OUTPUT_LIMIT_BYTES = 200_000


@lru_cache(maxsize=1)
def get_frontend() -> Computer:
    """The (cached) Computer targeting the AI4S login node."""
    return Computer(
        template="#!/bin/bash -l",
        host=config.ssh_host(),
        submitter="bash",
        python="python3",
    )


def run_command(cmd: str) -> str:
    """Run a shell command on the login node; return combined stdout+stderr.

    Output beyond OUTPUT_LIMIT_BYTES is truncated with a marker.
    """
    payload = 'cd "$HOME" && ' + cmd
    encoded = base64.b64encode(payload.encode()).decode()
    # remotemanager may print progress to stdout, which would corrupt the
    # MCP stdio transport — divert anything it emits.
    with contextlib.redirect_stdout(sys.stderr):
        result = get_frontend().cmd(
            f"echo {encoded} | base64 -d | bash -l", raise_errors=False,
        )
    output = result.stdout or ""
    if result.stderr:
        output = f"{output}\n{result.stderr}" if output else result.stderr
    if len(output) > OUTPUT_LIMIT_BYTES:
        output = (output[:OUTPUT_LIMIT_BYTES]
                  + f"\n[output truncated at {OUTPUT_LIMIT_BYTES} bytes]")
    return output


def write_remote_file(path: str, content: str) -> str:
    """Write a text file on the cluster, creating parent directories.

    Relative paths resolve against the home directory. Returns the absolute
    path of the written file; raises on failure.
    """
    path = norm_path(path)
    encoded = base64.b64encode(content.encode()).decode()
    quoted = shlex.quote(path)
    output = run_command(
        f'mkdir -p "$(dirname {quoted})" && '
        f"echo {encoded} | base64 -d > {quoted} && realpath {quoted}"
    )
    abs_path = output.strip().splitlines()[-1] if output.strip() else ""
    if not abs_path.startswith("/"):
        raise RuntimeError(f"Failed to write {path}: {output}")
    return abs_path
