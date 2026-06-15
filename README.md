# RikyuAgent

Claude Code plugin for the RIKEN AI4S supercomputer — submit and monitor Slurm jobs, manage files on the cluster, and search the official documentation, all from the agent.

## Install

In Claude Code:

```
/plugin marketplace add RIKEN-RCCS/Rikyu-Agent
/plugin install rikyu@rikyu-marketplace
/reload-plugins
```

Then run `/demo` to verify the connection end-to-end.

## Configuration

Settings live in `~/.rikyu/config.json`:

```json
{
  "ssh": {"host": "rikyu"}
}
```

`ssh.host` is a `~/.ssh/config` alias or `user@hostname` (key-based auth required). The env var `RIKYU_HOST` overrides the file.

For documentation search, add your API key for the RIKEN embedding service:

```json
{
  "ssh": {"host": "rikyu"},
  "embedding": {"api_key": "..."}
}
```

The env var `RIKYU_EMBED_API_KEY` overrides the file. Without it, docs search falls back to BM25 keyword search.

