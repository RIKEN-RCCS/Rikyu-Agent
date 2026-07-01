# Verify all transports conform

**Goal**: Prove every registered transport actually pulls a real file from the cluster to local disk with a matching checksum — the tier gate before benchmarking.
**Pre-conditions**:
- [ ] decouple_ssh_helpers merged (checksums work without a modern local rsync)
- [ ] cluster reachable; for `rm_rsync`, run with a ≥3.0 rsync first on PATH
**Success Gates**:
- ⬜ For each of `base64`, `scp`, `rsync`, `rm_rsync`: `download_file` returns `verified=True` on a real ~64 KB fixture [run]
- ⬜ Remote fixture is created and removed (no residue on the cluster) [run]
- ⬜ Transports unavailable in the current environment are reported as SKIP with the reason, not failures [run]
**References**: [transfer.py](server/rikyu_mcp/transfer.py) — `download_file`, `_TRANSPORTS`; earlier finding — `rm_rsync` needs `/opt/homebrew/bin` (rsync 3.4.4) ahead of `/usr/bin` (openrsync 2.6.9).

## Step 1: Implement the transport conformance check
**Goal**: One script that round-trips a tiny fixture through every registered transport.
**Implementation Logic**:
WHAT: New `server/tests/verify_transports.py` (CLI). Create a single ~64 KB random fixture on the remote via one `ssh` call; `transfer._ensure_transports_loaded()`; for each name in `sorted(transfer._TRANSPORTS)` (skip `_noop`): call `download_file(remote_fixture, tmp_local, name)` in a try/except, print `OK`/`SKIP(reason)`/`FAIL`; a transport that raises the remotemanager rsync-gate or a missing-binary error is a SKIP (environment), a checksum mismatch is a FAIL. Always remove the remote fixture and local temp files in a finally. Exit non-zero only on a genuine FAIL (verified=False or unexpected error), not on SKIP.
WHY: Guarantees the transport contract holds end-to-end against the live cluster before we spend a long benchmark on it; cleanly separates "environment can't run this transport here" (SKIP) from "this transport is broken" (FAIL).
**Deliverables**: `server/tests/verify_transports.py` (`make_remote_fixture`, `verify_one`, `main`).
**Consistency Checks**: `cd server && PATH="/opt/homebrew/bin:$PATH" uv run python tests/verify_transports.py` (expected: PASS — base64/scp/rsync/rm_rsync all OK)
**Commit**: `feat(bench): live transport conformance check`
