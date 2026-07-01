# Run sweep, pick default transport

**Goal**: Run the full good-citizen sweep, analyze the results, and choose the default transport + fallback order for the production tool.
**Pre-conditions**:
- [x] harness + probe + verify merged; all four transports pass live conformance
- [ ] cluster reachable; ≥3.0 rsync on PATH so rm_rsync participates
**Success Gates**:
- ⬜ Full sweep complete: 1K/1M/10M/100M × {base64,rm_rsync,rsync,scp}, 10 reps, serial, 3 s delay, remote fixtures cleaned up [run]
- ⬜ `__reports__/fs-download-rework/benchmark.{csv,md}` produced with wall-clock + integrity + token-cost [run]
- ⬜ A findings report names the chosen `DEFAULT_TRANSPORT` + `FALLBACK_ORDER` with the evidence [static]
**References**: [bench_download.py](server/tests/bench_download.py); earlier smoke — base64 fastest at ≤1 MB, all verified; token cost: 1 MB legacy ≈ 349 k tokens vs ~40 for metadata.

## Step 1: Execute + analyze the sweep (main thread)
**Goal**: Turn raw numbers into a transport decision.
**Implementation Logic**:
WHAT: Run `bench_download.py` with the agreed parameters (main thread, background). Read `benchmark.csv`/`benchmark.md`; identify the wall-clock crossover (base64's whole-file-in-memory cost vs rsync/scp streaming at 10 M/100 M), confirm all transfers `verified`, and quantify the legacy-vs-metadata token gap. Write a short findings report (use the writing-reports style) under `__reports__/fs-download-rework/` naming `DEFAULT_TRANSPORT` and an ordered `FALLBACK_ORDER` with rationale (correctness, portability per the probe, speed). These feed the rewrite_tool leaf.
WHY: The benchmark is the campaign's decision instrument; the default must be justified by data, not a guess.
**Deliverables**: `__reports__/fs-download-rework/benchmark.csv` + `benchmark.md` (from the harness); a findings report naming the chosen default + fallback order.
**Consistency Checks**: `test -s __reports__/fs-download-rework/benchmark.csv` (expected: PASS — report exists and is non-empty)
**Commit**: `docs(bench): full sweep results + chosen default transport`
