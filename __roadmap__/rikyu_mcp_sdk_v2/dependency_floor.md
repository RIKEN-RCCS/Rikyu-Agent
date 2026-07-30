# Dependency Floor

**Goal**: State the `hpc-agent-core>=0.4.6` requirement the code already depends on, so a fresh resolve cannot land on a version that breaks the import.
**Pre-conditions**:
- [ ] `hpc-agent-core` 0.4.6 is on PyPI and ships `hpc_agent_core/mcp_server.py`
- [ ] Local `uv` is available
**Success Gates**:
- ⬜ `uv run --directory server python -c "import importlib.metadata as m; print(m.version('hpc-agent-core'))"` prints 0.4.6 or higher
- ⬜ `uv run --directory server python -c "from rikyu_mcp import hpc_server, docs_server"` exits 0
- ⬜ `uv run --directory server python -c "import importlib.metadata as m; print(m.version('mcp'))"` prints a 2.x version
- ⬜ `server/run.sh`'s reinstall probe fails, and therefore reinstalls, when `hpc_agent_core.mcp_server` is absent
- ⬜ No changed file mentions this migration, a prior version's shortcomings, or the word "previously"
**References**: [R01 §Replay playbook](../../__reports__/mcp_sdk_v2_migration/00-knowledge_transfer_v0.md) — the apply table and per-target notes; rows 1–4 and 6–7 do not apply to Rikyu, which has no local `serving.py`/`middleware.py` and no tracked `uv.lock`

## Step 1: Raise the hpc-agent-core floor to 0.4.6
**Goal**: Make the declared dependency match what the source actually imports.
**Implementation Logic**:
`server/rikyu_mcp/hpc_server.py` and `docs_server.py` both import
`hpc_agent_core.mcp_server`, a module that exists only from `hpc-agent-core`
0.4.6. The declared floor `>=0.4,<0.5` therefore under-specifies: it is satisfied
by 0.4.4 and 0.4.5, neither of which ships that module, so a resolve or a stale
environment produces `ModuleNotFoundError` at server start. Raise the floor to
`>=0.4.6,<0.5`.
Extend the existing requirement comment in the same register as the line already
there (`# Needs >=0.4 for SchedulerBackend.get_live_resources()/get_drained_nodes().`)
— state what the floor is needed *for*, as a standing requirement. Do not narrate
what 0.4.5 lacked or why this is changing now; that belongs in the commit message.
Then re-sync the environment (`uv sync` / `uv run` in `server/`) so the local venv
stops holding 0.4.4, and confirm `mcp` resolves to 2.x transitively — this repo
does not declare `mcp` itself and must not start doing so.
**Deliverables**: `server/pyproject.toml` — `dependencies` entry `"hpc-agent-core>=0.4.6,<0.5"` plus its requirement comment naming `hpc_agent_core.mcp_server`
**Consistency Checks**: `uv run --directory server python -c "from hpc_agent_core.mcp_server import MCPServer; from rikyu_mcp import hpc_server, docs_server"` (expected: PASS)
**Commit**: `fix(deps): require hpc-agent-core>=0.4.6 for the MCPServer re-export`

## Step 2: Make run.sh's reinstall probe version-aware
**Goal**: Let the launcher self-heal an environment that satisfies the old floor but not the new one.
**Implementation Logic**:
`server/run.sh` reinstalls the package only when
`python -c "import rikyu_mcp, hpc_agent_core"` fails. That probe passes against
any `hpc-agent-core` release, so it cannot detect an environment whose core is
too old for the server to actually start — the launcher proceeds and the server
crashes instead.
Point the probe at the specific module the servers need,
`hpc_agent_core.mcp_server`, so the existence check and the real requirement
become the same check. This is a one-token change to the existing `if` condition;
leave the surrounding fallback logic, the `uv` fast path, and the comment alone.
**Deliverables**: `server/run.sh` — the `if ! "$VENV/bin/python" -c …` reinstall guard, importing `hpc_agent_core.mcp_server`
**Consistency Checks**: `bash -n server/run.sh && grep -q 'hpc_agent_core.mcp_server' server/run.sh` (expected: PASS)
**Commit**: `fix(run): probe the module the servers import, not just the package`

## Step 3: Bump the release version in lockstep
**Goal**: Ship the fix under a new version across all three manifests that carry one.
**Implementation Logic**:
The repo keeps `server/pyproject.toml`, `plugins/rikyu/.claude-plugin/plugin.json`
and `plugins/rikyu/.codex-plugin/plugin.json` at the same version — `f50d548`
moved all three from 0.4.3 to 0.4.4 together. Move all three from 0.4.4 to 0.4.5.
Change only the version field in each. Neither `marketplace.json` carries a
version and neither should gain one.
**Deliverables**: `server/pyproject.toml` (`version = "0.4.5"`), `plugins/rikyu/.claude-plugin/plugin.json` (`"version": "0.4.5"`), `plugins/rikyu/.codex-plugin/plugin.json` (`"version": "0.4.5"`)
**Consistency Checks**: `test $(grep -rho '0\.4\.5' server/pyproject.toml plugins/rikyu/.claude-plugin/plugin.json plugins/rikyu/.codex-plugin/plugin.json | wc -l) -eq 3` (expected: PASS)
**Commit**: `chore(release): bump to 0.4.5`
