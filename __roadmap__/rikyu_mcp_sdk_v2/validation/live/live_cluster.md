# Live Read-Only Verification

**Goal**: Run the repaired surface against the real Rikyu cluster read-only, and record the evidence — including the accounting question `AGENTS.md` still leaves open.
**Pre-conditions**:
- [ ] `tests/smoke.py --offline` passes
- [ ] Read-only SSH to Rikyu resolves via `~/.rikyu/config.json`
- [ ] A pre-run `squeue -u $USER` snapshot has been captured and saved
**Success Gates**:
- ⬜ `uv run --directory server python -m rikyu_mcp.doctor` reports every check passing, embedding aside, with the scheduler probe naming a live Slurm version
- ⬜ `uv run --directory server python tests/smoke.py` passes the read-only path end to end
- ⬜ `get_resources` returns the `gpu` partition with live per-state node counts, not static config
- ⬜ `run_command_on_cluster('hostname')` returns a Rikyu hostname
- ⬜ The `sacct` outcome is recorded in R03 whichever way it goes
- ⬜ `rikyu-hpc` and `rikyu-docs` both connect after a plugin reload and expose their tools
- ⬜ Post-run `squeue -u $USER` is identical to the pre-run snapshot
**References**: [R03 §Observability Requirements](../../../__reports__/rikyu_mcp_sdk_v2/00-test_definition_v0.md) — what a run must record; [R01 §Verify, in ascending cost](../../../__reports__/mcp_sdk_v2_migration/00-knowledge_transfer_v0.md) — the gate ordering and the instruction to stop at the first failure

## Step 1: Run the read-only gates against live Rikyu
**Goal**: Establish that the repaired servers work against the real scheduler, not just in isolation.
**Implementation Logic**:
Capture `squeue -u $USER` first and keep it — it is the only way to tell a leaked
job from one that was already queued, and the whole point of this leaf is that the
number of jobs does not change.
Then run the gates in ascending cost, stopping at the first failure: `rikyu-doctor`
(config, SSH, scheduler probe, embedding), then the read-only `tests/smoke.py`
path. Confirm `get_resources` returns live per-state node counts for the `gpu`
partition rather than static config — that distinction is the reason
`IRI_CHECKLIST.md` records a correction on this endpoint, so it is worth checking
explicitly rather than accepting any non-empty response.
Nothing in this step submits. If a gate appears to require a submitted job, stop
and escalate; do not submit.
Finish by re-capturing `squeue -u $USER` and diffing against the snapshot.
**Deliverables**: `__reports__/rikyu_mcp_sdk_v2/00-test_definition_v0.md` — an Evidence section recording the doctor output, the smoke output, the hpc and docs tool counts, the live `gpu` partition counts, and the pre/post queue snapshots
**Consistency Checks**: `uv run --directory server python -m rikyu_mcp.doctor && uv run --directory server python tests/smoke.py` (expected: PASS)
**Commit**: `docs(reports): record live read-only verification evidence for Rikyu`

## Step 2: Settle the accounting question and confirm the plugin round trip
**Goal**: Close the one cluster fact `AGENTS.md` flags as an unverified guess, and confirm the servers reach a real client.
**Implementation Logic**:
`AGENTS.md` records that `has_accounting=True` was inferred from
`hpc-agent-core`'s own docstring rather than observed, and asks whoever gains live
access to confirm a real `sacct` call returns data. The read-only harness already
calls `get_job_statuses([])`, which routes to `sacct` on an accounting cluster, so
the observation is free at this point.
Record what `sacct` actually returns. An empty result is a valid outcome, not a
failure: it would mean accounting is installed but returning nothing for this
account, which is a finding for a later cycle about
`SlurmBackend(has_accounting=True)` — not a blocker here, because the SDK
dependency work does not depend on it. Either way, update `AGENTS.md` so the fact
is stated rather than hedged, with no narrative about when or how it was checked.
Then reload the plugin and confirm both `rikyu-hpc` and `rikyu-docs` connect and
expose their tools. This is the only gate that exercises the path an actual user
takes, and it is the gate that currently fails.
**Deliverables**: `__reports__/rikyu_mcp_sdk_v2/00-test_definition_v0.md` — the `sacct` observation and the plugin-reload tool listing; `AGENTS.md` — the accounting fact stated rather than hedged
**Consistency Checks**: `uv run --directory server python -c "from rikyu_mcp import compute; print(len(compute.get_recent_statuses()))"` (expected: PASS)
**Commit**: `docs(agents): state Rikyu's accounting behaviour from observation`
