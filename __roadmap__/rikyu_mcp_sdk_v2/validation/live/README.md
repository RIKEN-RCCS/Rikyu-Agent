# Live Cluster

## Context
The campaign's final level, one depth below `harness_and_gating` because it runs
the harness that leaf produces. Consumes the tiered harness and the repaired
import; produces the live read-only evidence recorded in R03 and the answer to the
one cluster question `AGENTS.md` still lists as unverified.

## Goal
Prove the repaired surface against the real cluster without allocating any compute.

## Pre-conditions
- [ ] `tests/smoke.py --offline` passes
- [ ] Read-only SSH to Rikyu resolves via `~/.rikyu/config.json`
- [ ] A pre-run `squeue -u $USER` snapshot has been captured

## Success Gates
- ✅ `rikyu-doctor` reports every check passing, with the scheduler probe naming a live Slurm version
- ✅ `tests/smoke.py` read-only path passes end to end
- ✅ `get_resources` returns the `gpu` partition with live per-state node counts
- ✅ The `sacct` outcome behind `has_accounting=True` is recorded either way
- ✅ Both `rikyu-hpc` and `rikyu-docs` connect and expose their tools after a plugin reload
- ✅ Post-run `squeue -u $USER` matches the pre-run snapshot exactly

## Gotchas
- Nothing here submits. If a gate appears to need a submitted job, it is the gate that is wrong — stop and escalate rather than submitting.
- The `sacct` gate is an observation, not a pass/fail: an empty result is a valid, recordable outcome and a finding for a later cycle, not a blocker for this one.
- A pre-existing job in the queue must never be attributed to this run, which is what the pre-run snapshot is for.

## Status
```mermaid
graph TD
    live_cluster[Live Read-Only Verification]:::planned
    classDef done       fill:#166534,color:#bbf7d0
    classDef inprogress fill:#854d0e,color:#fef08a
    classDef planned    fill:#374151,color:#e5e7eb
    classDef amendment  fill:#1e3a5f,color:#bfdbfe
    classDef blocked    fill:#7f1d1d,color:#fecaca
```

## Nodes
| Node | Type | Status |
|:-----|:-----|:-------|
| `live_cluster.md` | 📄 Leaf Task | ⬜ Planned |

## Amendment Log
| ID | Date | Source | Nodes Added | Rationale |
|:---|:-----|:-------|:------------|:----------|

## Progress
| Node | Branch | Commits | Notes |
|:-----|:-------|:--------|:------|
