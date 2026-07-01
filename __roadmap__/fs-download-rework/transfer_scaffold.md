# transfer.py scaffold: dispatch, TransferResult, checksums

**Goal**: Create the transport-agnostic skeleton every transport plugs into — a dispatch entry point, a result type, and shared checksum/stdout-guard helpers — taking already-resolved concrete paths so it never imports config.
**Pre-conditions**:
- [ ] `server/` env resolves under `uv`
**Success Gates**:
- ⬜ `download_file(remote_path, local_dest, transport)` dispatches by name to a transport registry and raises a clear error for unknown transports [run]
- ⬜ `TransferResult` carries `local_path, bytes, sha256, verified, transport` [static]
- ⬜ `remote_sha256(path)` and `local_sha256(path)` helpers exist and agree on a tiny fixture [run]
- ⬜ Unit test importing the module and dispatching to a dummy registered transport passes under `uv run python -m pytest` [run]
**References**: [middleware.py](server/rikyu_mcp/middleware.py) — reuse `get_frontend()`, `quote_path`, and the `redirect_stdout(sys.stderr)` pattern (progress must never corrupt MCP stdio); [fs_checksum](server/rikyu_mcp/hpc_server.py:294) — `sha256sum` command for the remote side.

## Step 1: Scaffold transfer.py with registry, result type, and checksum helpers
**Goal**: Stand up the pluggable transport dispatch without implementing any real transport yet.
**Implementation Logic**:
WHAT: New module `server/rikyu_mcp/transfer.py`: (1) `@dataclass TransferResult` with fields `local_path: str, bytes: int, sha256: str, verified: bool, transport: str`. (2) A `_TRANSPORTS: dict[str, Callable]` registry + a `register(name)` decorator; each transport is `fn(remote_path: str, local_dest: Path) -> None` that lands bytes at `local_dest`. (3) `download_file(remote_path: str, local_dest, transport: str) -> TransferResult`: look up the transport (raise `ValueError(f"unknown transport {transport!r}; known: …")` if absent), compute `remote_sha256(remote_path)` first, call the transport, compute `local_sha256(local_dest)`, set `verified = (remote == local)`, return a populated `TransferResult`. (4) `remote_sha256(path)` via `run_command(f"sha256sum {quote_path(path)}")` parsing the first field; `local_sha256(path)` via `hashlib.sha256` streamed in chunks. (5) `run_capture(cmd) -> str` helper that runs a login-node command via `get_frontend().cmd(...)` capturing FULL stdout under `redirect_stdout(sys.stderr)` — explicitly NOT `run_command` (whose 200 KB truncation is the bug we are escaping); transports needing raw stdout (base64) use this. Register one trivial `"_noop"` transport used only by the unit test.
WHY: Decouples *mechanism* from *path policy* (config) and *tool wiring* (hpc_server). All four transport leaves then just add a `@register(...)` function in parallel without touching this file's contract.
**Deliverables**: `server/rikyu_mcp/transfer.py` (`TransferResult`, `register`, `_TRANSPORTS`, `download_file`, `remote_sha256`, `local_sha256`, `run_capture`, `_noop` transport); `server/tests/test_transfer_scaffold.py` (`test_dispatch_unknown_raises`, `test_dispatch_noop_verifies`).
**Consistency Checks**: `uv run python -m pytest server/tests/test_transfer_scaffold.py -q` (expected: PASS)
**Commit**: `feat(transfer): scaffold transport registry, TransferResult, checksum helpers`
