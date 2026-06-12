---
name: configuring
description: Use when the user wants to set up, configure, or troubleshoot RikyuAgent — SSH access to the AI4S cluster, the embedding endpoint for docs search (RAG), or the ~/.rikyu/config.json file. Also use when rikyu tools fail with connection or embedding errors.
---

# Configuring RikyuAgent

Settings live in `~/.rikyu/config.json` (env vars `RIKYU_HOST`,
`RIKYU_EMBED_BASE_URL`, `RIKYU_EMBED_API_KEY`, `RIKYU_EMBED_MODEL` override it):

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

## Guided setup — interview the user, then write the file

Read the existing `~/.rikyu/config.json` first (if any) and only ask about
what's missing or being changed.

1. **SSH** — ask how they reach the AI4S login node:
   - An alias in `~/.ssh/config` (recommended) → `"host": "<alias>"`.
   - Otherwise username + hostname → `"host": "user@login01.ai.r-ccs.riken.jp"`,
     and offer to add a proper alias block to `~/.ssh/config` instead.
   - Verify with: `ssh -o BatchMode=yes <host> 'echo ok'` (BatchMode matters —
     the MCP server cannot answer password prompts; key-based auth is required).
2. **Embedding endpoint** (optional — skippable, BM25 fallback works) — ask for:
   - `base_url`: the OpenAI-compatible base URL, ending in `/v1` (vLLM,
     text-embeddings-inference, llama.cpp server, and OpenAI itself all work).
   - `model`: the embedding model name the endpoint serves.
   - `api_key`: leave empty if the endpoint is unauthenticated.
3. **Write the file**, then `chmod 600 ~/.rikyu/config.json` — it may hold an
   API key. Never commit it or echo the key back in conversation.
4. **Validate** with the doctor (checks config, SSH, Slurm, endpoint, index):
   ```bash
   "$CLAUDE_PLUGIN_ROOT"/server/run.sh rikyu_mcp.doctor
   ```
   (From a checkout of the repo: `server/run.sh rikyu_mcp.doctor`.)
5. **If the embedding endpoint was added or changed**, rebuild the docs index
   so it gains vector embeddings:
   ```bash
   "$CLAUDE_PLUGIN_ROOT"/server/run.sh rikyu_mcp.rag.ingest
   ```
   Then run the doctor again — it should report "chunks with embeddings".

## Notes

- The embedding settings are read per-query, so docs search picks up changes
  immediately; an SSH host change needs the rikyu-hpc server restarted
  (reconnect MCP servers or restart Claude Code). A rebuilt docs index also
  needs the rikyu-docs server restarted to be picked up.
- If the endpoint is only reachable from inside the cluster network, tell the
  user to set up a tunnel (e.g. `ssh -L 8000:serving-host:8000 rikyu`) and use
  `http://localhost:8000/v1` as base_url.
