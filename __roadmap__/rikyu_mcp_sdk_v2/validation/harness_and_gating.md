# Smoke Harness and Submission Gate

**Goal**: Restructure the smoke harness into three tiers with a correct MCP v2 result contract, and gate the submitting tier behind an explicit opt-in.
**Pre-conditions**:
- [ ] `from rikyu_mcp import hpc_server, docs_server` imports cleanly
- [ ] R03 specifies the three tiers, the gating contract, and the observability requirement
**Success Gates**:
- ⬜ `uv run --directory server python tests/smoke.py --offline` passes with no Rikyu config present and no network
- ⬜ The offline tier asserts 26 hpc tools, 3 docs tools, and the presence of `submit_job`'s `$defs` for `Container`, `JobAttributes`, `ResourceSpec` and `VolumeMount`
- ⬜ `grep -rn "isError\|structuredContent\|inputSchema\|outputSchema" --include="*.py" server` returns nothing
- ⬜ `_text` no longer exists in `tests/smoke.py` and no call site passes `""` to `json.loads`
- ⬜ `tests/smoke.py --job` without the opt-in flag exits non-zero and prints no SSH activity
- ⬜ A `submit_job` tool call in a Claude Code session raises a user permission prompt rather than an auto-denial
- ⬜ The final line of every run reports passed / failed / skipped counts, with skips named
**References**: [R03 §Test Matrix](../../../__reports__/rikyu_mcp_sdk_v2/00-test_definition_v0.md) — tier ownership per row, fixtures strategy, observability requirement; [R01 §Verified compatibility](../../../__reports__/mcp_sdk_v2_migration/00-knowledge_transfer_v0.md) — the `mcp` v2 client contract, including that empty-list returns yield zero text content blocks

## Step 1: Give the harness a correct v2 result contract
**Goal**: Read tool results through the fields MCP v2 actually populates, and fail loudly when a call errors.
**Implementation Logic**:
The harness reads results with `_text(result)`, which returns `""` when
`result.content` is empty, and then asserts on truthiness. Two consequences: an
empty-list return (v2 emits zero text content blocks for one) is indistinguishable
from a failure, and a tool that errors is never detected at all — nothing inspects
`result.is_error`, so an errored call surfaces as a confusing assertion on empty
text rather than as the error it is.
Introduce two helpers. `call(session, name, args)` performs the call, asserts
`result.is_error is False` and, on failure, raises with the server's own error text
included so the diagnosis is in the failure message. `payload(result)` returns the
structured value, preferring `result.structured_content` and falling back to the
text blocks, so an empty list reads as an empty list and no call site ever hands
`""` to `json.loads`. Route every existing call site through them and delete
`_text`.
**Deliverables**: `server/tests/smoke.py` — `call(session, name, args)` and `payload(result)` helpers; `_text` removed; every `session.call_tool` site routed through `call`
**Consistency Checks**: `uv run --directory server python -c "import ast,sys; src=open('tests/smoke.py').read(); assert '_text' not in src; assert 'is_error' in src; assert 'structured_content' in src; ast.parse(src)"` (expected: PASS)
**Commit**: `test(smoke): read tool results via is_error and structured_content`

## Step 2: Split the harness into offline, read-only, and job tiers
**Goal**: Make the tool surface verifiable with no cluster, which is the coverage this repo lacks entirely.
**Implementation Logic**:
Today the first thing the harness does after listing tools is an SSH round trip,
so there is no way to check that the servers start and register their tools
without a configured cluster — precisely the failure this campaign exists to fix.
Split the checks into three tiers behind one entry point, per R03's matrix.
`--offline` starts both servers over stdio and exercises only what needs no SSH:
tool registration counts against the existing `_REQUIRED_HPC_TOOLS` and
`_REQUIRED_DOCS_TOOLS` sets, `submit_job`'s input schema including its nested
`$defs`, `get_facility` (static config), and `list_doc_sections` / `search_docs`
over the bundled index. Default (no flag) runs the offline tier and then the SSH
read-only checks. Keep `get_resources`' comment about being the first real round
trip accurate wherever it ends up.
Add the observability requirement: a run ends with passed / failed / skipped
counts, and a skipped group is named rather than silently folded into a pass.
Thread a run-scoped token through the job name so two concurrent runs cannot
collide on `rikyu-smoke-test`.
Update the module docstring, `README.md`'s Development block, and `AGENTS.md`'s
repo-map line for `tests/smoke.py` to describe the tiers as they now are — no
before-and-after framing.
**Deliverables**: `server/tests/smoke.py` — `--offline` flag, tiered `check_docs_server`/`check_hpc_server` split, run-scoped job-name token, end-of-run summary line; `README.md` Development block; `AGENTS.md` repo-map `tests/smoke.py` line
**Consistency Checks**: `env -u RIKYU_HOST uv run --directory server python tests/smoke.py --offline` (expected: PASS)
**Commit**: `test(smoke): add an offline tier that needs no cluster`

## Step 3: Gate the submitting tier behind an explicit opt-in
**Goal**: Make an accidental billable submission impossible to trigger with a single flag.
**Implementation Logic**:
Rikyu compute is billed. `--job` currently submits a real GPU job on one flag and
leaves it running, so a mistyped or copy-pasted command costs money. Require a
second, explicitly named opt-in flag: with `--job` alone the harness prints why it
refused, names the flag, and exits non-zero **before** constructing a client or
touching SSH.
Add the matching repo-scope guard in `.claude/settings.json` (a new file) via the
`update-config` skill: a `PreToolUse` hook returning
`hookSpecificOutput.permissionDecision: "ask"` so a submission attempt becomes a
user prompt. `"ask"` rather than `"deny"` — a denial is something an agent retries
against, a prompt is answered once and does not become a standing allow. The
matcher must cover the `Bash` forms (`smoke.py --job`, `sbatch`, `srun`, `salloc`)
and the submit tool under both names it can appear as: `mcp__rikyu-hpc__submit_job`
via a project `.mcp.json`, and `mcp__plugin_rikyu_rikyu-hpc__submit_job` via the
installed plugin. A matcher written against only one of those silently never fires.
This guard is a local developer utility. Nothing goes under `plugins/rikyu/`,
which ships to end users, and no cross-host equivalent is added.
**Deliverables**: `server/tests/smoke.py` — opt-in flag gating the `--job` path, refusal message naming the flag and the billing reason; `.claude/settings.json` — `PreToolUse` hook with `permissionDecision: "ask"` and a matcher covering both submit-tool names and the Bash submission commands
**Consistency Checks**: `! uv run --directory server python tests/smoke.py --job` (expected: PASS)
**Commit**: `test(smoke): require an explicit opt-in before submitting a billable job`
