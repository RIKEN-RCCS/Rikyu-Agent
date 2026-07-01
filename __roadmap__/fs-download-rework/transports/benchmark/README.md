# Benchmark & verification

## Context
<1-2 sentences: where this node fits in the parent campaign, what it depends on, what it produces>

## Goal
<One-line objective for this level>

## Pre-conditions
- [ ] <Measurable entry criteria>

## Success Gates
- ✅ <Measurable completion criteria>

## Status
```mermaid
graph TD
    verify_transports[Verify all transports conform]:::done
    benchmark_harness[bench_download.py harness]:::done
    portability_probe[rsync/scp portability probe]:::done
    finalize[Run experiments & productionize]:::planned
    classDef done       fill:#166534,color:#bbf7d0
    classDef inprogress fill:#854d0e,color:#fef08a
    classDef planned    fill:#374151,color:#e5e7eb
    classDef amendment  fill:#1e3a5f,color:#bfdbfe
    classDef blocked    fill:#7f1d1d,color:#fecaca
```

## Nodes
| Node | Type | Status |
|:-----|:-----|:-------|
| `verify_transports.md` | 📄 Leaf Task | ✅ Done |
| `benchmark_harness.md` | 📄 Leaf Task | ✅ Done |
| `portability_probe.md` | 📄 Leaf Task | ✅ Done |
| `finalize/` | 📁 Directory | ⬜ Planned |

## Amendment Log
| ID | Date | Source | Nodes Added | Rationale |
|:---|:-----|:-------|:------------|:----------|

## Progress
| Node | Branch | Commits | Notes |
|:-----|:-------|:--------|:------|
