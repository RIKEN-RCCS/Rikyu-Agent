# RikyuAgent

Claude Code plugin for the RIKEN AI4S supercomputer — submit and monitor Slurm jobs, manage files on the cluster, and search the official documentation, all from the agent.

## Install

In Claude Code:

```
/plugin marketplace add RIKEN-RCCS/Rikyu-Agent
/plugin install rikyu
```

Then run `/demo` to verify the connection end-to-end.

## Configuration

Settings live in `~/.rikyu/config.json`:

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

`ssh.host` is a `~/.ssh/config` alias or `user@hostname` (key-based auth required).
`embedding` points at any OpenAI-compatible `/v1/embeddings` endpoint; omit it to fall back to BM25 keyword search. Env vars `RIKYU_HOST`, `RIKYU_EMBED_BASE_URL`, `RIKYU_EMBED_API_KEY`, `RIKYU_EMBED_MODEL` override the file.

Ask the agent to configure it (`configuring` skill), or validate manually:

```bash
server/run.sh rikyu_mcp.doctor
```