# rikyu_mcp_sdk_v2

## Context
Completes the plugin family's `mcp` 1.x → 2.0.0 migration for Rikyu. Unlike the
banyan and dgx1 siblings — which carry their own `serving.py`/`middleware.py` and
needed a 6-line `FastMCP` → `MCPServer` rename — Rikyu is a thin skin on the
`hpc-agent-core` PyPI package, so its migration is a **dependency contract**.
Commit `f50d548` already switched both servers to
`from hpc_agent_core.mcp_server import MCPServer`, but that module ships only in
`hpc-agent-core` 0.4.6 while `pyproject.toml` still declares `>=0.4,<0.5` — so
`main` currently raises `ModuleNotFoundError` and both MCP servers fail to start.
Produces: a working import, a stated floor, a tiered offline-capable test harness,
and a PR to `RIKEN-RCCS/Rikyu-Agent`.

## Reference Documents
- [R01 MCP SDK v2 knowledge transfer](../../__reports__/mcp_sdk_v2_migration/00-knowledge_transfer_v0.md) — the replay playbook from banyan/dgx1: pre-flight audit greps, apply table, verified-compatibility matrix
- [R02 smoke --job test definition](../../__reports__/mcp_sdk_v2_migration/00-test_definition_v0.md) — upstream R1–R8 risks this campaign must triage for Rikyu
- [R03 Rikyu test definition](../../__reports__/rikyu_mcp_sdk_v2/00-test_definition_v0.md) — produced by this campaign; risk table and matrix for the three smoke tiers

## Goal
Restore a working MCP server surface on a stated `hpc-agent-core>=0.4.6` floor, with an offline test tier that catches this breakage class without a cluster.

## Pre-conditions
- [ ] `hpc-agent-core` 0.4.6 is published and ships `hpc_agent_core/mcp_server.py`
- [ ] Local `uv` is available (no mamba env exists for this project)
- [ ] Read-only SSH to Rikyu resolves (`~/.rikyu/config.json` → `ssh.host`)
- [ ] Pre-flight audit greps return zero hits for v1-era APIs and camelCase wire fields

## Success Gates
- ✅ `from rikyu_mcp import hpc_server, docs_server` imports cleanly and `mcp` resolves to 2.x
- ✅ `tests/smoke.py --offline` passes with no SSH configured, asserting 26 hpc + 3 docs tools
- ✅ `tests/smoke.py` read-only path and `rikyu-doctor` pass against live Rikyu
- ✅ Zero jobs submitted: `squeue -u $USER` is identical before and after the campaign
- ✅ No tracked source, config, or user-facing doc references this migration
- ✅ PR opened against `RIKEN-RCCS/Rikyu-Agent`

## Gotchas
- **Rikyu compute is billed and the project has no usage limit configured.** Cluster interaction throughout this campaign is read-only. `tests/smoke.py --job`, `submit_job`, `sbatch`, `srun` and `salloc` are gated behind explicit in-session user confirmation and are never a Success Gate. Refactoring the `--job` code path is in scope; executing it is not.
- **`hpc-agent-core` is read-only to this repo** (`AGENTS.md` design rule #1). Every fix lands in `server/rikyu_mcp/` or the dependency declaration, never in the installed package.
- **No meta-discourse in source artifacts** — they must read as if always written that way. Migration narrative belongs here, in R03, and in commit messages only.
- **`0.4.5` is a trap.** It already requires `mcp>=2.0,<3.0` but does not ship the `hpc_agent_core.mcp_server` re-export, so it satisfies a naive "needs mcp v2" floor while still breaking the import. The floor must be `0.4.6`.

## Status
```mermaid
graph TD
    dependency_floor[Dependency Floor]:::done
    test_definition[Test Definition Report]:::done
    docs_sync[Docs and Repo Config Sync]:::done
    validation[Validation]:::done
    classDef done       fill:#166534,color:#bbf7d0
    classDef inprogress fill:#854d0e,color:#fef08a
    classDef planned    fill:#374151,color:#e5e7eb
    classDef amendment  fill:#1e3a5f,color:#bfdbfe
    classDef blocked    fill:#7f1d1d,color:#fecaca
```

## Nodes
| Node | Type | Status |
|:-----|:-----|:-------|
| `dependency_floor.md` | 📄 Leaf Task | ✅ Done |
| `test_definition.md` | 📄 Leaf Task | ✅ Done |
| `docs_sync.md` | 📄 Leaf Task | ✅ Done |
| `validation/` | 📁 Directory | ✅ Done |

## Amendment Log
| ID | Date | Source | Nodes Added | Rationale |
|:---|:-----|:-------|:------------|:----------|

## Progress
| Node | Branch | Commits | Notes |
|:-----|:-------|:--------|:------|
