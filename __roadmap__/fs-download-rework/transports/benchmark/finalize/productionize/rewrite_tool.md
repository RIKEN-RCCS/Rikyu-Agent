# Rewrite fs_download to new contract

**Goal**: Replace the base64-in-context `fs_download` with a write-to-disk tool that transfers via the benchmarked default transport and returns metadata only.
**Pre-conditions**:
- [ ] experiments done — the default transport + fallback order are chosen from the benchmark
- [ ] config.resolve_local_dest + transfer.download_file available (foundation)
**Success Gates**:
- ⬜ `fs_download(path, local_path=None, transport=None) -> dict` returns `{local_path, bytes, sha256, verified, transport}` and NEVER file bytes [static]
- ⬜ No size cap and no base64/`run_command` path remain in the tool [static]
- ⬜ A >146 KB file round-trips with `verified=True` (old silent-truncation gone) [run, live]
- ⬜ `transport=None` uses the benchmarked default; an unavailable transport falls back per the chosen order [run]
**References**: [hpc_server.py:300](server/rikyu_mcp/hpc_server.py:300) — current `fs_download`; [transfer.py](server/rikyu_mcp/transfer.py) — `download_file`, `_TRANSPORTS`; [config.py](server/rikyu_mcp/config.py) — `resolve_local_dest`; experiments outcome — chosen default + fallback.

## Step 1: Rewrite the fs_download tool
**Goal**: Wire the tool to the transfer layer; delete the base64-in-context behavior.
**Implementation Logic**:
WHAT: In `hpc_server.py`, replace `fs_download` with `fs_download(path: str, local_path: str | None = None, transport: str | None = None) -> dict`. Resolve `dest = config.resolve_local_dest(path, local_path)`; pick `transport or DEFAULT_TRANSPORT`; call `transfer.download_file(path, dest, chosen)`; if it raises an availability error (remotemanager rsync-gate / missing binary), walk a small `FALLBACK_ORDER` (from the benchmark, e.g. rsync → scp → base64) until one succeeds, recording which ran. Return `dataclasses.asdict(result)`. Add module constants `DEFAULT_TRANSPORT` and `FALLBACK_ORDER` set from the experiments outcome. Update the docstring: transfers host→local disk, returns metadata only, deliberate deviation from IRI GET /filesystem/download (point to IRI_CHECKLIST.md). Remove the 5 MB cap, the `stat`, and the `base64` call entirely.
WHY: This is the whole point — bytes go to disk as a side-effect; the tool result is small metadata, eliminating the token-blowup + silent-truncation failure modes.
**Deliverables**: `server/rikyu_mcp/hpc_server.py` (rewritten `fs_download`; `DEFAULT_TRANSPORT`, `FALLBACK_ORDER` constants).
**Consistency Checks**: `cd server && PATH="/opt/homebrew/bin:$PATH" uv run python -c "import asyncio; ..."` — a live download of a >146 KB file returning metadata with verified=True and a small result (main thread will run the exact check). Offline: `uv run pytest tests/ -q` still green.
**Commit**: `feat(fs): fs_download writes to disk and returns metadata (no base64-in-context)`
