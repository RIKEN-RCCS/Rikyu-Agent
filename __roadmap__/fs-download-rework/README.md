# fs-download-rework

## Context
`fs_download` currently returns a file's base64 as the tool result, routing bytes through the LLM
context — this has caused real tool-call failures (sub-5 MB files exceeding the ~10k-token tool
output cap) and a latent silent-truncation bug (>146 KB files corrupt via `run_command`'s 200 KB cap).
This campaign replaces it with a write-to-disk + metadata contract, benchmarks four transports to pick
the default, then productionizes the tool. Consumers: the `rikyu-hpc` MCP server and its downstream
ports (banyan, dgx1).

## Goal
Replace base64-in-context `fs_download` with a host→local-disk transfer returning metadata only, default transport chosen from a rigorous, good-citizen benchmark.

## Pre-conditions
- [ ] `uv`-managed `server/` environment resolves (`uv sync`)
- [ ] SSH access to Rikyu login node works (`uv run rikyu-doctor` passes)
- [ ] `remotemanager` 0.14.3 present (ships rsync/scp transports)

## Success Gates
- ✅ `fs_download` never returns file bytes; tool result is metadata `{local_path, bytes, sha256, verified, transport}` [static]
- ✅ A >146 KB file round-trips correctly (old silent-truncation path is gone) [run]
- ✅ Benchmark report under `__reports__/` compares all 4 transports on wall-clock, token cost, integrity/resumability, portability, and names the chosen default + fallback order [run]
- ✅ `uv run python server/tests/smoke.py` passes with the new contract [run]

## Status
```mermaid
graph TD
    config_and_paths[Config download_dir + local path safety]:::done
    transfer_scaffold[transfer.py scaffold: dispatch, TransferResult, checksums]:::done
    transports[Transport implementations]:::done
    decouple_ssh_helpers[Decouple transfer helpers from remotemanager (direct ssh)]:::done
    analysis[Analysis: plots + token scaling + findings artifact]:::done
    classDef done       fill:#166534,color:#bbf7d0
    classDef inprogress fill:#854d0e,color:#fef08a
    classDef planned    fill:#374151,color:#e5e7eb
    classDef amendment  fill:#1e3a5f,color:#bfdbfe
    classDef blocked    fill:#7f1d1d,color:#fecaca
```

## Nodes
| Node | Type | Status |
|:-----|:-----|:-------|
| `config_and_paths.md` | 📄 Leaf Task | ✅ Done |
| `transfer_scaffold.md` | 📄 Leaf Task | ✅ Done |
| `transports/` | 📁 Directory | ✅ Done |
| `decouple_ssh_helpers.md` | 📄 Leaf Task | ✅ Done |
| `analysis/` | 📁 Directory | ✅ Done |

## Amendment Log
| ID | Date | Source | Nodes Added | Rationale |
|:---|:-----|:-------|:------------|:----------|

## Progress
| Node | Branch | Commits | Notes |
|:-----|:-------|:--------|:------|
