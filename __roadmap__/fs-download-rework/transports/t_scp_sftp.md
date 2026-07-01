# scp subprocess + optional paramiko SFTP

**Goal**: A universally-available `scp` transport plus an optional, import-gated paramiko SFTP transport as the no-CLI fallback.
**Pre-conditions**:
- [ ] `transfer.py` scaffold merged; `transports/` package exists
**Success Gates**:
- ⬜ Module registers transport name `"scp"` [run]
- ⬜ `"sftp"` is registered IFF `paramiko` is importable (currently NOT installed → not registered) [run]
- ⬜ Pure `_scp_argv(host, remote_path, local_dest)` builds the expected argv in a unit test (offline) [run]
**References**: [config.py](server/rikyu_mcp/config.py) — `ssh_host()`.

## Step 1: Implement the scp (+ optional SFTP) transport as its own module
**Goal**: Self-contained module; do not edit `transfer.py` or `__init__.py`.
**Implementation Logic**:
WHAT: New file `server/rikyu_mcp/transports/t_scp_sftp.py`. Pure `_scp_argv(host, remote_path, local_dest) -> list[str]` → `["scp", "-p", f"{host}:{remote_path}", str(local_dest)]`. `@register("scp")` runs it via `subprocess.run(..., check=True, stdout=sys.stderr, stderr=subprocess.PIPE, text=True)` using `config.ssh_host()`. Then, guarded by `try: import paramiko` / `except ImportError: paramiko = None`: if available, define and `@register("sftp")` a transport that opens an `SSHClient`/`SFTPClient` to `config.ssh_host()` and `sftp.get(remote_path, str(local_dest))`. If paramiko is absent, register nothing for sftp (no error).
WHY: `scp` is the universal fallback where GNU rsync is absent (relevant to the banyan/dgx1 ports); SFTP is the no-external-CLI fallback but must not become a hard dependency.
**Deliverables**: `server/rikyu_mcp/transports/t_scp_sftp.py` (`_scp_argv`, `scp_transport` registered `"scp"`, conditional `sftp_transport`); `server/tests/test_transport_scp.py` (`test_scp_registered`, `test_scp_argv`, `test_sftp_registration_matches_paramiko_availability`).
**Consistency Checks**: `cd server && uv run python -m pytest tests/test_transport_scp.py -q` (expected: PASS)
**Commit**: `feat(transfer): add scp transport and optional paramiko SFTP fallback`
