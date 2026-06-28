# RikyuAgent

Claude Code and Codex plugin for the RIKEN **AI4S** supercomputer — submit and monitor Slurm jobs, manage files on the cluster, and search the official documentation, all from the agent.

AI4S is a GPU-first system: 216 NVIDIA Grace + GB200 nodes (4 GPUs each, aarch64).

## Install

### Prerequisite: uv

The plugin starts its MCP servers with `uv tool run` from this repository's
`main` branch, so `uv` must be installed and available on your PATH before
Claude Code or Codex starts the plugin.

Common install options:

```bash
brew install uv
```

or:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

After installing uv, restart Claude Code or Codex so the plugin process inherits
the updated PATH.

### Claude Code

Install in Claude Code:

```
/plugin marketplace add RIKEN-RCCS/Rikyu-Agent
/plugin install rikyu@rikyu-marketplace
/reload-plugins
```

### Codex

Install in Codex:

```
codex plugin marketplace add RIKEN-RCCS/Rikyu-Agent
```

Then open `/plugins`, install `rikyu`, start a new thread, and run `/ai4s-demo`
to verify the connection end-to-end.

### Manual (any MCP-compatible client)

Clone the repository wherever you prefer:

```bash
git clone https://github.com/RIKEN-RCCS/Rikyu-Agent.git
```

#### Option A — Using Hatch!

[Hatch!](https://github.com/CrackingShells/Hatch) registers MCP servers on
any supported host from a single command. Install it once, then configure
both servers — replace `/path/to/Rikyu-Agent` with the actual clone location
and `<host>` with your target platform (`claude-code`, `codex`, `cursor`,
`vscode`, `claude-desktop`, `kiro`, `gemini`, `lmstudio`, or any other
[supported host](https://github.com/CrackingShells/Hatch#supported-mcp-hosts)):

```bash
pip install hatch-xclam

hatch mcp configure rikyu-hpc --host <host> \
  --command uv --args "run" "--directory" "/path/to/Rikyu-Agent/server" "rikyu-hpc-mcp"

hatch mcp configure rikyu-docs --host <host> \
  --command uv --args "run" "--directory" "/path/to/Rikyu-Agent/server" "rikyu-docs-mcp"
```

To replicate the same configuration to additional hosts:

```bash
hatch mcp sync --from-host <host> --to-host cursor,vscode
```

#### Option B — Edit `.mcp.json` directly

Create or edit `.mcp.json` in your project root, replacing `/path/to/Rikyu-Agent`
with the actual clone location:

```json
{
  "mcpServers": {
    "rikyu-hpc": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/Rikyu-Agent/server", "rikyu-hpc-mcp"],
      "env": {}
    },
    "rikyu-docs": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/Rikyu-Agent/server", "rikyu-docs-mcp"],
      "env": {}
    }
  }
}
```

#### Verify

Whichever option you chose, run the doctor check to verify connectivity:

```bash
uv run --directory /path/to/Rikyu-Agent/server rikyu-doctor
```

## Configuration

Settings live in `~/.rikyu/config.json`:

```json
{
  "ssh": {"host": "rikyu"}
}
```

`ssh.host` is a `~/.ssh/config` alias or `user@hostname` (key-based auth required). The env var `RIKYU_HOST` overrides the file.

For documentation search, add your API key for the shared RIKEN embedding service:

```json
{
  "ssh": {"host": "rikyu"},
  "embedding": {"api_key": "..."}
}
```

The env var `RCCS_EMBED_API_KEY` sets the key. With it, docs search uses semantic (vector) matching; without it — or off the RIKEN network — it falls back to BM25 keyword search over the same content.
