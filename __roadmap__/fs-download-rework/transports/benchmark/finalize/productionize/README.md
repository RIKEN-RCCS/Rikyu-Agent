# Productionize fs_download

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
    rewrite_tool[Rewrite fs_download to new contract]:::done
    tests_and_docs[Update smoke.py, IRI_CHECKLIST, docstrings]:::planned
    deploy_rsync_env[Enforce rsync>=3.0 at deploy via MCP env/PATH config]:::planned
    classDef done       fill:#166534,color:#bbf7d0
    classDef inprogress fill:#854d0e,color:#fef08a
    classDef planned    fill:#374151,color:#e5e7eb
    classDef amendment  fill:#1e3a5f,color:#bfdbfe
    classDef blocked    fill:#7f1d1d,color:#fecaca
```

## Nodes
| Node | Type | Status |
|:-----|:-----|:-------|
| `rewrite_tool.md` | 📄 Leaf Task | ✅ Done |
| `tests_and_docs.md` | 📄 Leaf Task | ⬜ Planned |
| `deploy_rsync_env.md` | 📄 Leaf Task | ⬜ Planned |

## Amendment Log
| ID | Date | Source | Nodes Added | Rationale |
|:---|:-----|:-------|:------------|:----------|

## Progress
| Node | Branch | Commits | Notes |
|:-----|:-------|:--------|:------|
