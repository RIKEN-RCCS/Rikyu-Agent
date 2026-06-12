# RikyuAgent

Claude Code plugin for the RIKEN AI4S supercomputer. Two MCP servers + skills.
The HPC tool surface follows the [IRI Facility API](https://api.alcf.anl.gov/)
(`api.pdf`), executed on the cluster over SSH via remotemanager.
Coverage: [IRI_CHECKLIST.md](IRI_CHECKLIST.md).

## Tools

**rikyu-hpc** (Slurm on AI4S, needs `ssh rikyu` working):

| Group | Tools |
|---|---|
| facility | `get_facility` |
| status | `get_resources` |
| compute | `submit_job` (JobSpec → sbatch), `get_job_status`, `get_job_statuses`, `cancel_job` |
| filesystem | `fs_ls`, `fs_stat`, `fs_view`, `fs_head`, `fs_tail`, `fs_mkdir`, `fs_upload` |
| extension | `run_command_on_cluster` |

**rikyu-docs** (RAG over the AI4S docs, no SSH needed):
`search_docs`, `list_doc_sections`, `read_doc_section`
— BM25 for now; vector search activates once `RIKYU_EMBED_BASE_URL` (+ `RIKYU_EMBED_MODEL`) point at an OpenAI-compatible embeddings endpoint.

**Skills**: `configuring`, `submitting-jobs`, `monitoring-jobs`, `ai4s-reference`.

## Configuration

Settings live in `~/.rikyu/config.json` — ask the agent to set it up (the
`configuring` skill guides it), or write it yourself:

```json
{
  "ssh": {"host": "rikyu"},
  "embedding": {
    "base_url": "https://your-serving-host/v1",
    "api_key": "...",
    "model": "your-embedding-model"
  }
}
```

`ssh.host` is a `~/.ssh/config` alias or `user@hostname` (key-based auth).
`embedding` points at any OpenAI-compatible `/v1/embeddings` endpoint; leave
it out to use BM25 keyword search. Env vars `RIKYU_HOST`,
`RIKYU_EMBED_BASE_URL`, `RIKYU_EMBED_API_KEY`, `RIKYU_EMBED_MODEL` override
the file. Validate everything with:

```bash
server/run.sh rikyu_mcp.doctor
```

## Layout

```
.claude-plugin/        plugin + marketplace manifests
.mcp.json              launches both servers via server/run.sh (auto-venv)
server/rikyu_mcp/
  models.py            JobSpec / JobStatus / JobState (PSI/J style)
  compute.py           JobSpec → sbatch, status parsing
  middleware.py        remotemanager SSH layer (login shell, $HOME-relative paths)
  hpc_server.py        the rikyu-hpc MCP tools
  docs_server.py       the rikyu-docs MCP tools
  rag/                 embed client, index store, ingest pipeline
data/ai4s_config.json  static cluster facts
data/docs_index/       pre-built docs index
skills/                the three skills
```

## Use it

```bash
# install in Claude Code
/plugin marketplace add /Users/wddawson/Desktop/RikyuAgent
/plugin install rikyu@rikyu-marketplace

# test live (from server/)
.venv/bin/python tests/smoke.py        # read-only
.venv/bin/python tests/smoke.py --job  # + submits a tiny 5-min job

# rebuild the docs index (from server/)
.venv/bin/python -m rikyu_mcp.rag.ingest
```
