# Decouple transfer helpers from remotemanager (direct ssh)

**Goal**: Make `transfer.py`'s remote exec + checksum helpers run over a direct `ssh` subprocess instead of `remotemanager`, so downloads work on hosts where remotemanager's eager rsync≥3.0 version gate blocks (e.g. macOS/openrsync 2.6.9).
**Pre-conditions**:
- [x] transfer.py scaffold + transports merged
**Success Gates**:
- ⬜ `run_capture` and `remote_sha256` no longer import/call `remotemanager` (via `get_frontend`/`run_command`) — they use a direct `ssh` subprocess [static]
- ⬜ Pure `_ssh_argv(host, cmd)` builds the expected argv; unit-tested offline [run]
- ⬜ Existing scaffold + transport unit tests still pass (`uv run pytest tests/ -q`) [run]
- ⬜ On this macOS/openrsync box, `remote_sha256` of a real remote file succeeds (proves the gate is bypassed) — LIVE, tiny file [run]
**References**: [transfer.py](server/rikyu_mcp/transfer.py) — current `run_capture`/`remote_sha256`; [middleware.py](server/rikyu_mcp/middleware.py) — `quote_path` (reuse) and the home-relative path convention; [config.py](server/rikyu_mcp/config.py) — `ssh_host()`.

## Step 1: Replace remotemanager exec with a direct ssh subprocess in transfer.py
**Goal**: Swap the remote-exec mechanism under `run_capture`/`remote_sha256` without changing their signatures or the transport contract.
**Implementation Logic**:
WHAT: In `server/rikyu_mcp/transfer.py`: add pure `_ssh_argv(host: str, cmd: str) -> list[str]` → `["ssh", host, f"cd $HOME && {cmd}"]` (home-relative, matching the server convention). Add `_ssh_capture(cmd: str) -> str`: `from rikyu_mcp import config`; `argv = _ssh_argv(config.ssh_host(), cmd)`; `proc = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)`; on non-zero raise `RuntimeError(proc.stderr.strip() or f"ssh exited {proc.returncode}")`; return `proc.stdout`. Rewrite `run_capture(cmd)` to delegate to `_ssh_capture(cmd)` (keep the docstring explaining it captures FULL stdout — no 200 KB truncation, which is the bug being fixed — and now also avoids remotemanager's rsync version gate). Rewrite `remote_sha256(path)` to `_ssh_capture(f"sha256sum {quote_path(path)}").split()[0]`. Remove the now-unused `get_frontend`/`run_command` imports and the `contextlib.redirect_stdout` (subprocess stdout is captured to PIPE, so it can't corrupt MCP stdio). Keep `quote_path` import (from middleware).
WHY: remotemanager builds an rsync transport and version-checks it (≥3.0.0) at `Computer` construction, so any host with older/BSD rsync can't even run `.cmd()`. Our transfer layer only needs plain SSH exec + a checksum; a direct `ssh` subprocess is simpler, dependency-light, and portable. (The separate `rm_rsync` transport intentionally keeps using remotemanager — its availability is one of the benchmark's portability findings.)
**Deliverables**: `server/rikyu_mcp/transfer.py` (new `_ssh_argv`, `_ssh_capture`; rewritten `run_capture`, `remote_sha256`; imports cleaned); `server/tests/test_ssh_helpers.py` (`test_ssh_argv`, `test_remote_sha256_parses_first_field` with `_ssh_capture` monkeypatched).
**Consistency Checks**: `cd server && uv run pytest tests/ -q` (expected: PASS — all existing tests plus the new ones)
**Commit**: `refactor(transfer): run exec+checksum over direct ssh, not remotemanager`
