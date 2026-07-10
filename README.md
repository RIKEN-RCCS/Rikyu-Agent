# RIKYU Agent

A Claude Code / Codex plugin for the [Supercomputer RIKYU](https://docs.r-ccs.riken.jp/rikyu/en/),
a RIKEN Center for Computational Science (R-CCS) system built for
AI-accelerated scientific discovery — 400 nodes of NVIDIA GB200 NVL4
(1,600 B200 GPUs total). It lets an agent submit and monitor Slurm jobs,
manage files, and search RIKYU's documentation, over SSH.

Built as a thin machine-specific "skin" on top of
[`hpc-agent-core`](https://pypi.org/project/hpc-agent-core/) — see
[`PORTING.md`](PORTING.md) for the porting guide this repo follows, and
[`AGENTS.md`](AGENTS.md) for the design rules and cluster facts an agent
working on this repo should know.

## What's here

```
plugins/rikyu/            Claude Code / Codex plugin: skills + MCP wiring
server/                   The rikyu_mcp Python package (depends on hpc-agent-core)
docs/                     Source PDFs of RIKYU's official user guide (reference only —
                           not shipped to users; see server/rikyu_mcp/data/rikyu_guide.md
                           for the hand-written guide actually bundled with the plugin)
```

## Install

1. Install the server package (its dependency, `hpc-agent-core`, pulls in
   the MCP SDK, `remotemanager`, etc.):

   ```
   cd server
   python3 -m venv .venv
   .venv/bin/pip install -e .
   ```

   Make sure the resulting console scripts (`rikyu-hpc-server`,
   `rikyu-docs-server`, `rikyu-doctor`) are on `PATH` when Claude
   Code/Codex launches — e.g. by activating `.venv`, or installing with
   `pipx install ./server`.

2. Add this repo as a plugin marketplace (Claude Code: `.claude-plugin/marketplace.json`
   at the repo root; Codex: `.agents/plugins/marketplace.json`), then
   install the `rikyu` plugin from it.

3. Configure access — see the `rikyu-configuring` skill, or by hand:

   - Register an SSH key with RIKYU via Open OnDemand's "SSH Public Key" app.
   - Write `~/.hpc-agent/rikyu.json`:
     ```json
     {"ssh": {"host": "USERNAME@login.rikyu.r-ccs.riken.jp"}}
     ```
     (or `"host": "rikyu"` if you already have that `Host` alias in `~/.ssh/config`).
   - `RIKYU_HOST` overrides this for a one-off session without writing the file.

4. Verify:

   ```
   rikyu-doctor
   ```

   All lines should read `✓` except possibly embedding (falls back to
   keyword search outside RIKEN's network — not blocking).

## What the plugin can do

- **Jobs**: `submit_job`, `get_job_status`/`get_job_statuses`, `cancel_job`,
  `update_job` — a thin wrapper over Slurm (`sbatch`/`sacct`/`scancel`/`scontrol`).
- **Files**: `fs_ls`, `fs_stat`, `fs_view`, `fs_head`, `fs_tail`, `fs_mkdir`,
  `fs_upload`, `fs_download`, `fs_checksum`, `fs_cp`, `fs_mv`, `fs_chmod`,
  `fs_chown`, `fs_symlink`, `fs_compress`, `fs_extract`.
- **Facility info**: `get_facility`, `get_resources`, `get_resource` — RIKYU's
  partitions, GPU/node/CPU/memory table, storage tiers, modules, Spack.
  `run_command_on_cluster` for anything else on the login node.
- **Docs search**: `search_docs`, `list_doc_sections`, `read_doc_section`
  over a hand-written guide (`server/rikyu_mcp/data/rikyu_guide.md`), not a
  live fetch of the official site.

See [`IRI_CHECKLIST.md`](IRI_CHECKLIST.md) for what maps to the IRI
Facility API spec, what's deferred, and what's a RIKYU-specific extension.

## RIKYU quick facts

Single Slurm partition (`gpu`, all 400 nodes). GPUs requested as a
job-total count (`--gpus=N`), only 1/2/3/4/8/12/16 accepted; node count is
derived automatically at 4 GPUs/node. 96-hour wall-time cap. Three storage
tiers: home (5 GB, `/home/USER`), group (1 TB, `/data1/GROUP`), node-local
scratch (1.5 TB/GPU, `/tmp`, wiped at job end). Compiler toolchains via
Lmod (`nvhpc` and variants); applications via Spack. Billed per GPU-hour
during Early Access Phase 2. Full detail: `server/rikyu_mcp/data/rikyu_guide.md`,
or ask the agent to `search_docs`.

## Development

```
cd server
.venv/bin/python -m rikyu_mcp.doctor          # health check
.venv/bin/python tests/smoke.py               # read-only MCP stdio test
.venv/bin/python tests/smoke.py --job          # + submits a real 1-GPU job
```

Rebuilding the docs index after editing `rikyu_guide.md`:

```
cd server
python -c "from rikyu_mcp import config"      # sanity check
python -m hpc_agent_core.rag.ingest
```

Commit the resulting `rikyu_mcp/data/docs_index/` (chunks.json, and
embeddings.npy if an embedding API key was configured at ingest time).
