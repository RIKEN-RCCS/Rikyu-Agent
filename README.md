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

## Configure

Settings live in `~/.hpc-agent/rikyu.json` (the common directory shared by
every hpc-agent-core plugin):

```json
{
  "ssh": {"host": "rikyu"}
}
```

- `ssh.host` is a `~/.ssh/config` alias or `user@login.rikyu.r-ccs.riken.jp`
  (key-based auth required — register your key via Open OnDemand's "SSH
  Public Key" app first). `RIKYU_HOST` overrides the file.
- A legacy `~/.rikyu/config.json` is still read if it's the only config
  present.

For documentation search, add your API key for the shared RIKEN embedding
service:

```json
{
  "ssh": {"host": "rikyu"},
  "embedding": {"api_key": "..."}
}
```

`RIKYU_EMBED_API_KEY` (or the shared `RCCS_EMBED_API_KEY`) sets the key.
With it, docs search uses semantic (vector) matching; without it — or off
the RIKEN network — it falls back to BM25 keyword search over the same
content. The `rikyu-configuring` skill walks through this interactively.

## Install

### Prerequisite: uv

The plugin starts its MCP servers with `uv tool run` from this repository's
`main` branch, so [`uv`](https://docs.astral.sh/uv/) must be installed and
on your `PATH` before Claude Code or Codex starts the plugin:

```bash
brew install uv        # or: curl -LsSf https://astral.sh/uv/install.sh | sh
```

Restart Claude Code or Codex after installing uv so the plugin process
inherits the updated `PATH`.

### Claude Code

```
/plugin marketplace add RIKEN-RCCS/Rikyu-Agent
/plugin install rikyu@rikyu-marketplace
/reload-plugins
```

### Codex

```
codex plugin marketplace add RIKEN-RCCS/Rikyu-Agent
```

Then open `/plugins`, install `rikyu`, start a new thread, and run
`/rikyu-demo` to verify the connection end-to-end.

### Manual (any MCP-compatible client)

Create or edit `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "rikyu-hpc": {
      "command": "uv",
      "args": ["tool", "run", "--quiet", "--from", "git+https://github.com/RIKEN-RCCS/Rikyu-Agent.git@main#subdirectory=server", "rikyu-hpc-mcp"],
      "env": {}
    },
    "rikyu-docs": {
      "command": "uv",
      "args": ["tool", "run", "--quiet", "--from", "git+https://github.com/RIKEN-RCCS/Rikyu-Agent.git@main#subdirectory=server", "rikyu-docs-mcp"],
      "env": {}
    }
  }
}
```

## Verify

```bash
uv tool run --quiet --from git+https://github.com/RIKEN-RCCS/Rikyu-Agent.git@main#subdirectory=server rikyu-doctor
```

All lines should read `✓` except possibly embedding (falls back to keyword
search outside RIKEN's network — not blocking).

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
python3 -m venv .venv && .venv/bin/pip install -e .
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
