# Direct rsync subprocess

**Goal**: A transport that shells out to `rsync` directly for maximum control over resume/checksum flags.
**Pre-conditions**:
- [ ] `transfer.py` scaffold merged; `transports/` package exists
**Success Gates**:
- ⬜ Module registers transport name `"rsync"` [run]
- ⬜ Pure `_rsync_argv(host, remote_path, local_dest)` builds the expected argv in a unit test (offline) [run]
- ⬜ subprocess stdout redirected to stderr; non-zero exit raises [static]
**References**: [config.py](server/rikyu_mcp/config.py) — `ssh_host()` for the SSH alias.

## Step 1: Implement the direct rsync subprocess transport as its own module
**Goal**: Self-contained module; do not edit `transfer.py` or `__init__.py`.
**Implementation Logic**:
WHAT: New file `server/rikyu_mcp/transports/t_rsync_subprocess.py`. Pure `_rsync_argv(host: str, remote_path: str, local_dest: Path) -> list[str]` → `["rsync", "-az", "--checksum", "--partial", f"{host}:{remote_path}", str(local_dest)]`. `@register("rsync")` `def rsync_transport(remote_path, local_dest):` → `from rikyu_mcp import config`; `argv = _rsync_argv(config.ssh_host(), remote_path, local_dest)`; `subprocess.run(argv, check=True, stdout=sys.stderr, stderr=subprocess.PIPE, text=True)` (raise `RuntimeError` with stderr on `CalledProcessError`).
WHY: Baseline efficient delta transfer with `--partial` resume; comparison point against the RemoteManager wrapper.
**Deliverables**: `server/rikyu_mcp/transports/t_rsync_subprocess.py` (`_rsync_argv`, `rsync_transport`, registered `"rsync"`); `server/tests/test_transport_rsync.py` (`test_rsync_registered`, `test_rsync_argv`).
**Consistency Checks**: `cd server && uv run python -m pytest tests/test_transport_rsync.py -q` (expected: PASS)
**Commit**: `feat(transfer): add direct rsync subprocess download transport`
