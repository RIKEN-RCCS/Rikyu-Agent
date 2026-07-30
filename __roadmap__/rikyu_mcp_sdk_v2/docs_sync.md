# Docs and Repo Config Sync

**Goal**: Bring `AGENTS.md`'s repo map back in step with the dependency declaration and add the two standing rules an agent working here needs, without recording any of this migration.
**Pre-conditions**:
- [ ] `AGENTS.md` has been read in full, including its design-rules numbering
**Success Gates**:
- ⬜ `grep -rn '0\.3,<0\.4' AGENTS.md` returns nothing
- ⬜ `AGENTS.md` states the "never import the MCP SDK directly" rule as a numbered design rule alongside the existing six
- ⬜ `AGENTS.md` states, as a standing cluster fact, that Rikyu compute is billed and a submission needs explicit user confirmation
- ⬜ `git status --porcelain` does not list `__reports__/mcp_sdk_v2_migration`
- ⬜ No added line references this migration, this session, `mcp` 1.x, or a prior `hpc-agent-core` version's shortcomings
**References**: [R01 §The migration surface](../../__reports__/mcp_sdk_v2_migration/00-knowledge_transfer_v0.md) — its "MECHANICAL" row covers docstring/prose naming; for Rikyu the equivalent surface is `AGENTS.md`'s repo map, since `middleware.py` lives in core

## Step 1: Correct the repo map and add the two standing rules
**Goal**: Make `AGENTS.md` accurate about the dependency and explicit about the two constraints it currently leaves implicit.
**Implementation Logic**:
`AGENTS.md`'s repository map annotates `server/pyproject.toml` as depending on
`hpc-agent-core>=0.3,<0.4`. That is two floor bumps stale and now contradicts the
file it describes. Correct it to the current declaration.
Add a seventh design rule: the MCP SDK is never imported directly — server
construction comes from `hpc_agent_core.mcp_server`. This is the invariant that
makes an SDK rename a one-file change in core instead of an edit here, and it is
currently enforced only by the fact that the code happens to do it. Write it in
the same imperative register as rules 1–6.
Add one cluster fact: Rikyu compute is billed, so a job submission needs explicit
user confirmation. Place it with the other RIKYU cluster facts. It reinforces
design rule 5 ("Show before you run") with the reason that rule matters most here.
State all three timelessly, as standing facts and rules. Nothing about a prior
version, an SDK migration, or when this was learned.
**Deliverables**: `AGENTS.md` — corrected `pyproject.toml` line in the Repository map; new numbered design rule for `hpc_agent_core.mcp_server`; new billing entry under RIKYU cluster facts
**Consistency Checks**: `! grep -q '0\.3,<0\.4' AGENTS.md && grep -q 'hpc_agent_core.mcp_server' AGENTS.md && grep -qi 'billed' AGENTS.md` (expected: PASS)
**Commit**: `docs(agents): correct the core dependency pin; state the SDK-import and billing rules`

## Step 2: Ignore the shared report symlink
**Goal**: Keep an untracked cross-repo symlink out of `git status`.
**Implementation Logic**:
`__reports__/mcp_sdk_v2_migration` is a symlink into the `lbc-llm-agents`
monorepo, the same arrangement as `__reports__/banyan_port` and
`__reports__/dgx1_port` — both of which `.gitignore` already lists by exact path.
Add the third entry beside them, so the directory reads consistently and the
symlink stops appearing as an untracked path.
This must not exclude `__reports__/rikyu_mcp_sdk_v2/`, which is a real directory
this campaign tracks. Use the same exact-path form as the neighbouring entries
rather than a glob.
**Deliverables**: `.gitignore` — `__reports__/mcp_sdk_v2_migration` entry adjacent to the existing `banyan_port` and `dgx1_port` lines
**Consistency Checks**: `git check-ignore -q __reports__/mcp_sdk_v2_migration && ! git check-ignore -q __reports__/rikyu_mcp_sdk_v2` (expected: PASS)
**Commit**: `chore(git): ignore the shared mcp_sdk_v2_migration report symlink`
