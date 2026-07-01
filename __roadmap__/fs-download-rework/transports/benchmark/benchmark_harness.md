# bench_download.py harness

**Goal**: A good-citizen benchmark that measures every transport across file sizes on wall-clock, integrity, and token/context cost, and quantifies the token cost of the legacy base64-in-context tool it replaces.
**Pre-conditions**:
- [ ] decouple_ssh_helpers merged; transports verified
- [ ] cluster reachable; run with ≥3.0 rsync first on PATH so `rm_rsync` participates
**Success Gates**:
- ⬜ Sweeps sizes {1 KB, 1 MB, 10 MB, 100 MB} × transports {base64, scp, rsync, rm_rsync}, serial, `--repetitions` default 10, `--delay` between transfers, `--max-size` cap; NO 1 GB [run]
- ⬜ Records per (size, transport): wall-clock mean/min/max, `verified`, and marks unavailable transports SKIP [run]
- ⬜ Reports token/context cost: legacy base64 result size (bytes + est. tokens ≈ chars/4) vs new metadata (~fixed), flagging which sizes breach a ~10k-token tool cap [run]
- ⬜ Creates each remote fixture, transfers, then deletes it immediately; logs total bytes moved [run]
- ⬜ Writes `__reports__/fs-download-rework/benchmark.csv` and a markdown summary table [run]
**References**: [transfer.py](server/rikyu_mcp/transfer.py) — `download_file`; [smoke.py](server/tests/smoke.py) — existing MCP `ClientSession` `call()` pattern; [hpc_server.py](server/rikyu_mcp/hpc_server.py) — the legacy `fs_download` tool (still base64 at this point) for a real token-cost measurement.

## Step 1: Implement the benchmark harness
**Goal**: One CLI script producing the decision table, respecting the shared filesystem.
**Implementation Logic**:
WHAT: New `server/tests/bench_download.py`. Args: `--sizes` (default `1K,1M,10M,100M`), `--repetitions` (default 10), `--delay` (seconds between transfers, default e.g. 2.0), `--max-size`, `--transports` (default all registered minus `_noop`), `--host`. For each size: make one remote fixture via `ssh` (`dd`/`head -c`); for each transport: run `transfer.download_file` `--repetitions` times **strictly serially**, sleeping `--delay` between runs, timing each with `time.perf_counter`; collect wall-clock mean/min/max and `verified` (any mismatch → flag). Compute the legacy token cost analytically (`b64_bytes = ceil(size/3)*4`; `est_tokens = b64_bytes/4`) AND, for the smallest size only, call the real legacy `fs_download` MCP tool once via the `smoke.py` `ClientSession` pattern and record the actual serialized result length for ground truth. New-path token cost = size of the metadata dict (~tens of tokens, constant). Delete each remote fixture immediately after its transports finish (finally block); accumulate and print total bytes moved. Emit `__reports__/fs-download-rework/benchmark.csv` (one row per size×transport×metric) and a compact markdown table. Optional `--resume` flag runs a separate qualitative check: start a 100 MB transfer, interrupt it, re-run, and record whether it resumed (rsync `--partial`) or restarted (scp/base64) — clearly labelled, not part of the timed sweep. Print an explicit note of any size/transport that was capped or skipped (no silent truncation of coverage).
WHY: This is the campaign's decision instrument — it must be representative, reproducible (10 reps), and a good citizen on an early-access shared machine (serial, spaced, ≤100 MB, immediate cleanup). The legacy-vs-new token comparison is the headline justification for the whole rework.
**Deliverables**: `server/tests/bench_download.py` (`parse_sizes`, `make_fixture`, `bench_one`, `legacy_token_cost`, `measure_legacy_tool`, `write_report`, `main`); outputs `__reports__/fs-download-rework/benchmark.csv` + `.md`.
**Consistency Checks**: `cd server && PATH="/opt/homebrew/bin:$PATH" uv run python tests/bench_download.py --sizes 1K,1M --repetitions 2 --delay 1` (expected: PASS — a fast smoke of the harness itself; full run happens in experiments)
**Commit**: `feat(bench): download benchmark harness (wall-clock, integrity, token cost)`
