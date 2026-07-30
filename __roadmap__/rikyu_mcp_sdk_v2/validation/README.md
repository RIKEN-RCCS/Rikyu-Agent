# Validation

## Context
Sits after the campaign's three level-0 leaves because nothing here can execute
until the import is repaired: a stdio client cannot start a server that raises
`ModuleNotFoundError`. Consumes `dependency_floor`'s working import and
`test_definition`'s tier specification; produces a harness whose offline tier
proves the tool surface with no cluster, and the live read-only evidence that
closes the campaign.

## Goal
Prove the repaired MCP surface, first without a cluster and then against the live one, read-only throughout.

## Pre-conditions
- [ ] `from rikyu_mcp import hpc_server, docs_server` imports cleanly
- [ ] The three smoke tiers and the `--job` gating contract are specified in R03

## Success Gates
- ✅ `tests/smoke.py --offline` passes with no SSH configured and no cluster reachable
- ✅ No `isError`, `structuredContent`, `inputSchema` or `outputSchema` attribute access remains in `server/`
- ✅ `--job` without its opt-in flag exits non-zero before any SSH round trip
- ✅ The live read-only path and `rikyu-doctor` pass against Rikyu
- ✅ `squeue -u $USER` is unchanged across this whole level

## Gotchas
- Read-only only. No leaf at this level may submit a job, and no Success Gate here depends on one having been submitted.
- The `--offline` tier is the load-bearing new capability: it is the only gate that would have caught this campaign's originating defect without a cluster, so it must genuinely run with no config present rather than merely tolerating a missing one.

## Status
```mermaid
graph TD
    harness_and_gating[Smoke Harness and Submission Gate]:::planned
    live[Live Cluster]:::planned
    classDef done       fill:#166534,color:#bbf7d0
    classDef inprogress fill:#854d0e,color:#fef08a
    classDef planned    fill:#374151,color:#e5e7eb
    classDef amendment  fill:#1e3a5f,color:#bfdbfe
    classDef blocked    fill:#7f1d1d,color:#fecaca
```

## Nodes
| Node | Type | Status |
|:-----|:-----|:-------|
| `harness_and_gating.md` | 📄 Leaf Task | ⬜ Planned |
| `live/` | 📁 Directory | ⬜ Planned |

## Amendment Log
| ID | Date | Source | Nodes Added | Rationale |
|:---|:-----|:-------|:------------|:----------|

## Progress
| Node | Branch | Commits | Notes |
|:-----|:-------|:--------|:------|
