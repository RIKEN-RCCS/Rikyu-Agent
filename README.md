# RikyuAgent

Claude Code plugin for the RIKEN AI4S supercomputer — submit and monitor Slurm jobs and manage files on the cluster, all from the agent.

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

