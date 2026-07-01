# Transport implementations

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
    t_base64[Enhanced base64 + local write]:::planned
    t_remotemanager_rsync[RemoteManager rsync wrapper]:::planned
    t_rsync_subprocess[Direct rsync subprocess]:::planned
    t_scp_sftp[scp subprocess + optional paramiko SFTP]:::planned
    benchmark[Benchmark & verification]:::planned
    classDef done       fill:#166534,color:#bbf7d0
    classDef inprogress fill:#854d0e,color:#fef08a
    classDef planned    fill:#374151,color:#e5e7eb
    classDef amendment  fill:#1e3a5f,color:#bfdbfe
    classDef blocked    fill:#7f1d1d,color:#fecaca
```

## Nodes
| Node | Type | Status |
|:-----|:-----|:-------|
| `t_base64.md` | 📄 Leaf Task | ⬜ Planned |
| `t_remotemanager_rsync.md` | 📄 Leaf Task | ⬜ Planned |
| `t_rsync_subprocess.md` | 📄 Leaf Task | ⬜ Planned |
| `t_scp_sftp.md` | 📄 Leaf Task | ⬜ Planned |
| `benchmark/` | 📁 Directory | ⬜ Planned |

## Amendment Log
| ID | Date | Source | Nodes Added | Rationale |
|:---|:-----|:-------|:------------|:----------|

## Progress
| Node | Branch | Commits | Notes |
|:-----|:-------|:--------|:------|
