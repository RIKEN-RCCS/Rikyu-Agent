# Test Definition Report

**Goal**: Produce the Rikyu-scoped test-definition report that triages R01/R02's risk set for this repo and specifies the three smoke tiers before they are built.
**Pre-conditions**:
- [ ] R02's R1–R8 risk set has been read in full
- [ ] Rikyu's current `server/tests/smoke.py` has been read in full
**Success Gates**:
- ⬜ Every risk R1–R8 from R02 carries a Rikyu verdict of *fixed*, *not-applicable*, or *deferred*, each with a stated reason
- ⬜ Every row of the test matrix maps to exactly one of the three tiers (`--offline`, read-only, `--job`)
- ⬜ The report states the `--job` gating contract and names billing as a trust-boundary constraint
- ⬜ `__reports__/rikyu_mcp_sdk_v2/` is a real tracked directory, not a symlink, and `git status` shows both files as additions
- ⬜ The report is round-versioned `00-…_v0.md` with a sibling `README.md`, matching the `Octopus-Agent/__reports__/octopus_port/` precedent
**References**: [R02 §Risks](../../__reports__/mcp_sdk_v2_migration/00-test_definition_v0.md) — the eight risks and the audit sweep it demands of "rikyu · octopus · shinobu lab"

## Step 1: Triage R02's risk set against Rikyu's actual harness
**Goal**: Answer the sweep R02 asks every sibling repo to run, with evidence rather than assumption.
**Implementation Logic**:
R02 defines eight risks found while validating the migration on banyan and dgx1,
and its matrix includes an explicit audit row requiring each sibling repo to be
"marked fixed / not-applicable with a reason". Rikyu's `tests/smoke.py` is an
older, simpler harness than the one R02 was written against, so several risks do
not transfer and a blanket copy of R02's conclusions would be wrong.
Read Rikyu's harness first, then decide each verdict from what the code does.
Expected shape, to be confirmed not assumed: R1 (`update_job` privilege) — the
harness never calls `update_job`; R2 (job leak) — applies, and the harness already
documents leaving the job running, so this is deferred behaviour rather than a
latent defect; R3 (container self-skip) — no container block exists; R4 (empty-list
returns yield zero text blocks) — applies, `_text()` returns `""` and callers
assert on truthiness; R5 (poll-timeout ambiguity) — no poll loop exists; R6 (fixed
paths and job names) — applies, `rikyu-smoke-test` is a constant; R7 (hand-run
only) — applies; R8 (camelCase wire fields) — clean, zero hits.
Record each verdict with the specific line or absence that justifies it.
**Deliverables**: `__reports__/rikyu_mcp_sdk_v2/00-test_definition_v0.md` — Executive Summary, Scope (in/out/assumptions/trust boundaries incl. billing), Risks table with a Rikyu verdict column for R1–R8
**Consistency Checks**: `test -d __reports__/rikyu_mcp_sdk_v2 && test ! -L __reports__/rikyu_mcp_sdk_v2 && grep -c '^| R[1-8] ' __reports__/rikyu_mcp_sdk_v2/00-test_definition_v0.md` (expected: PASS)
**Commit**: `docs(reports): triage the smoke-harness risk set for Rikyu`

## Step 2: Specify the three tiers and the gating contract
**Goal**: Define what each tier must prove, so the harness leaf implements a spec rather than improvising one.
**Implementation Logic**:
Write the test matrix and supporting sections. The matrix must partition coverage
across exactly three tiers and say, for each row, which tier owns it: `--offline`
(no SSH — tool registration, `submit_job` schema `$defs`, `get_facility`, docs
search over the bundled index), read-only (adds the SSH round trips), and `--job`
(mutating, gated).
State the gating contract explicitly: Rikyu compute is billed, so `--job` requires
a second opt-in flag, must refuse before any SSH round trip when that flag is
absent, and is never a Success Gate for this campaign. Cover the fixtures strategy
(a run-scoped token threaded through job names), and the observability requirement
that a run ends with a machine-readable passed/failed/skipped summary in which a
skip is distinguishable from a pass.
Add the sibling `README.md` following the round-versioned index convention used by
`__reports__/mcp_sdk_v2_migration/README.md` — Documents, Status, Related.
**Deliverables**: `__reports__/rikyu_mcp_sdk_v2/00-test_definition_v0.md` — Test Matrix, Fixtures / Test Data Strategy, Observability Requirements, Minimal Must-Run Regression Set, Scope Control Notes, Handover Notes; `__reports__/rikyu_mcp_sdk_v2/README.md` — Documents, Status, Related sections
**Consistency Checks**: `grep -qi 'offline' __reports__/rikyu_mcp_sdk_v2/00-test_definition_v0.md && grep -qi 'billed\|billing' __reports__/rikyu_mcp_sdk_v2/00-test_definition_v0.md && test -f __reports__/rikyu_mcp_sdk_v2/README.md` (expected: PASS)
**Commit**: `docs(reports): specify the three smoke tiers and the --job gating contract`
