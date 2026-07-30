# `tests/smoke.py` — Rikyu Test Definition (v0)

Date: 2026-07-30

> Triages R02's eight risks
> ([00-test_definition_v0.md](../mcp_sdk_v2_migration/00-test_definition_v0.md))
> against Rikyu's actual harness, and specifies the three smoke tiers and the
> `--job` gating contract the `harness_and_gating` leaf implements. R02 was
> written against a harness with a poll loop, a container-skip path, and an
> `update_job` privilege probe; Rikyu's `server/tests/smoke.py` has none of
> those, so several risks do not transfer. Each verdict below is read off the
> code, not copied from R02's conclusions.

## Executive Summary

- **What must be proven:** that Rikyu's harness surface — 26 hpc tools, 3 docs
  tools, one `--job` path — is verifiable without a cluster wherever that is
  possible, that the eight risks R02 found are individually triaged rather than
  inherited wholesale, and that a mistyped or copy-pasted `--job` cannot submit
  a billable job on RIKYU compute.
- **Top risks and how the suite addresses them:** four of R02's eight risks
  apply to Rikyu's harness (R2, R4, R6, R7) and get matrix rows; four do not
  (R1, R3, R5, R8) because the code path they describe is either absent or
  already clean — see the Risks table. R4 (empty-list contract) and R6
  (run-scoped naming) get regression coverage; R2 (job leak) is deferred by
  design, not fixed, per this campaign's scope; R7 (hand-run only) is answered
  by adding an `--offline` tier that *can* run without an operator or a
  cluster.
- **Estimated test volume and tiers:** 13 scenarios — 6 offline (regression),
  1 development (wire-field audit) + 1 development (this report, satisfying
  R02's sibling-repo audit row), 3 read-only (regression), 2 `--job`
  (1 regression/no-SSH gate check that runs every campaign, 1 integration
  `end_to_end` that is never executed by this campaign or by CI).

## Scope

### In scope
- `server/tests/smoke.py` in full: its current single read-only-plus-`--job`
  shape, and its restructuring into three tiers.
- The MCP v2 result contract the harness must read results through
  (`is_error`, `structured_content`) — R01's client contract, R04's manifestation
  in this file.
- The `--job` gating contract: what a second opt-in flag must prove before the
  harness is allowed to touch SSH.
- The sibling-repo audit row R02's own Test Matrix demands ("rikyu · octopus ·
  shinobu lab", each "marked fixed / not-applicable with a reason") — this
  report *is* Rikyu's answer to that row.

### Out of scope
- Executing `--job` against live RIKYU. RIKYU compute is billed and the
  project has no usage limit configured; this campaign's Success Gates never
  require a submission, and the two-flag gate this report specifies exists
  precisely so a submission cannot happen by accident.
- Fixing R2 (the job leak). Rikyu's harness already documents leaving the
  submitted job running (its module docstring: "does not wait for it to
  finish or clean it up"); adding a cleanup guard is a real improvement but is
  not in this campaign's Success Gates and is not proposed here as a test.
- `update_job` coverage (R1). The harness never calls `update_job`; there is
  no privileged-vs-unprivileged behavior in this file to probe.
- Container/`.sif` coverage (R3). No such code path exists in this harness.
- `compute.py` / scheduler translation — untouched by this migration, out of
  scope on the same grounds R02 gave.

### Assumptions
- Rikyu has Slurm accounting enabled (`has_accounting=True`, corroborated by
  `hpc-agent-core`'s own `SlurmBackend` docstring per `AGENTS.md`), so
  `get_job_statuses` is a real `sacct`-backed call here, unlike banyan/dgx1's
  no-accounting deployments R02 was validated against.
- The account may be unprivileged on Rikyu, same default assumption R02 makes;
  moot here since `update_job` is never called.
- `~/.rikyu/config.json` / `RIKYU_HOST` may be entirely absent in CI or on a
  fresh clone — the offline tier's whole purpose is to hold in that case.

### Trust boundaries
| Dependency | Mocked or real | Why |
|---|---|---|
| MCP stdio transport (offline tier) | **real** | Both servers actually start over stdio; only the SSH-backed tools are avoided, not the transport |
| Slurm scheduler / SSH (read-only tier) | **real** | Same reasoning as R02 — mocking it proves nothing about the actual port |
| Slurm scheduler / SSH (`--job` tier) | **real, but gated** | Billed compute; real Slurm is the point, but every invocation of this tier requires an explicit second opt-in and is never run by this campaign |
| Docs index (`rikyu_mcp/data/docs_index/`) | **real, bundled** | Ships in the repo; no network needed, so it belongs in the offline tier |
| Embedding endpoint | absent → BM25 fallback | Not relevant to the job/tool-registration risks in scope here |

## Risks

R02's eight risks, triaged against what `server/tests/smoke.py` actually does
(as of this report; line numbers refer to that file's current contents).

| ID | Risk (from R02) | Rikyu Verdict | Reason |
|---|---|---|---|
| R1 | `update_job` asserts a privileged operation; fails on unprivileged accounts | **not-applicable** | `update_job` appears exactly once in the file — in `_REQUIRED_HPC_TOOLS` (line 27), a registration-count set. No call site ever invokes it (`session.call_tool("update_job", …)` does not occur anywhere). There is no privileged-operation behavior in this harness to fail. |
| R2 | No cleanup guard — failure between submit and cancel leaks a running job | **applies, deferred** | `submit_job` is called at lines 89–99 with no surrounding `try`/`finally` and no matching `cancel_job` call anywhere in the file (`cancel_job` likewise only appears in the tool set, line 27). This is not a silent leak, though: the module docstring (lines 7–11) already states the job is left running by design — "does not wait for it to finish or clean it up ... check on it and scancel/let it run to completion yourself." Rikyu's shape differs from R02's finding: there is no submit→cancel window to fail inside, because there is no cancel step at all. Verdict is *deferred*, not *fixed*, because a cleanup guard would still be a real improvement — it is just out of this campaign's scope (see Out of scope, above). |
| R3 | Container coverage self-skips on `NO_SIF`; a skip reads as a pass | **not-applicable** | Zero hits for `NO_SIF`, `.sif`, or `container` anywhere in `server/tests/smoke.py`. No container code path exists to self-skip. |
| R4 | Empty-list tool returns yield zero text blocks; `json.loads("")` raises | **applies** | `_text()` (lines 36–37) returns `""` when `result.content` is empty. Three call sites then assert on that return value's truthiness — `_text(sections).strip()` (line 51), `_text(results).strip()` (line 55), `_text(facility).strip()` (line 71) — so a legitimate empty-list success would fail those assertions exactly like a real error. `json.loads` is not currently called anywhere in this file, so the specific `json.loads("")` crash R02 observed has not manifested here yet — but the underlying contract violation (truthiness-testing `_text()`'s output) is present and would bite the moment a call site parses that text as JSON, or the moment a currently-print-only call site (`get_job_statuses([])`, line 83–84) grows an assertion. |
| R5 | Poll-loop exhaustion is indistinguishable from job failure in the output | **not-applicable** | No poll loop exists anywhere in this file (zero hits for `poll`, `sleep`, `timeout`). `submit_job` prints a job id and returns; nothing waits on job completion. |
| R6 | Fixed `/tmp` paths and job names — two concurrent runs on one cluster collide | **applies (job-name half only)** | `"name": "rikyu-smoke-test"` (line 91) is a string literal with no per-run token, so two concurrent `--job` runs would collide. The "fixed paths" half does not apply: this harness performs no `fs_*` filesystem calls at all, so there is no `/tmp` path to collide on. |
| R7 | `--job` runs only by hand, so these defects surface late and per-operator | **applies** | No CI configuration exists in this repo (no `.github/` directory). `README.md`'s Development block and `AGENTS.md`'s repo map both document `tests/smoke.py` as a command run by hand (`cd server && uv run python tests/smoke.py[ --job]`), and `AGENTS.md` states plainly that it "need[s] real SSH access to RIKYU to mean anything." |
| R8 | Other camelCase wire fields may remain (the `is_error` class of bug) | **not-applicable, clean** | `grep -rn "isError\|structuredContent\|inputSchema\|outputSchema" --include="*.py" server` returns zero hits. No camelCase wire-field attribute access exists anywhere in this repo's Python source. |

Note on the file this triage is read against: `git ls-files server/tests`
lists exactly one tracked file, `smoke.py`. Nothing else in
`server/tests/__pycache__` or elsewhere is a live test; this repo has no
tracked test beyond the one file this report analyzes.

## Test Matrix

Three tiers own this coverage, one entry point: `--offline` (no SSH, can run
in CI with no Rikyu access at all), the default read-only path (adds SSH round
trips against live Rikyu), and `--job` (mutating, gated behind a second opt-in
flag, never run by this campaign). The `Tier` column names which of the three
owns each row; a parenthetical marks anything that departs from that tier's
usual resource cost (e.g. a `--job`-tier scenario that itself needs no SSH).

| Group | Scenario | Risk it covers | Tier | Setup / Data | Assertion (observable) |
|------:|----------|----------------|------|--------------|-------------------------|
| Registration | Both servers list their required tool names with no cluster config present (parameterized over hpc/docs) | R7 | offline (regression) | Start `rikyu_mcp.hpc_server` and `rikyu_mcp.docs_server` over stdio each with `RIKYU_HOST` unset and no `~/.rikyu/config.json` | `list_tools()` names are a superset of `_REQUIRED_HPC_TOOLS` (26) / `_REQUIRED_DOCS_TOOLS` (3); no SSH connection is attempted by either process |
| Schema | `submit_job`'s input schema exposes nested `$defs` for `Container`, `JobAttributes`, `ResourceSpec`, `VolumeMount` | none (net-new offline coverage this campaign exists to add) | offline (regression) | Read `submit_job`'s tool definition out of the offline `list_tools()` response | All four keys are present under `$defs` |
| Static config | `get_facility` returns non-empty facility data with no SSH | none (existing coverage, correctly offline-safe already) | offline (regression) | Call with no cluster config reachable | `payload(result)` is non-empty |
| Docs index | `list_doc_sections` / `search_docs` return content from the bundled index, no network | none (existing coverage, correctly offline-safe already) | offline (regression) | Bundled `rikyu_mcp/data/docs_index/` (chunks.json), no embedding endpoint reachable | `list_doc_sections` returns ≥1 section; `search_docs` returns ≥1 hit for a known query |
| Isolation | The `--job` path's job name is built from a run-scoped token, not the literal `rikyu-smoke-test` | R6 | offline (regression) | Extract the name-generation step into a callable helper; invoke it twice in one process, no SSH | Neither invocation returns the literal string `rikyu-smoke-test`; the two invocations return different names |
| Contract | `call()`/`payload()` read every result through `is_error` and `structured_content`, never `_text()`/`json.loads("")` | R4, R8 | offline (regression) | Any offline tool call (e.g. `get_facility`) | The helper exposes `result.is_error`; `payload()` prefers `structured_content` and only falls back to text when it is absent |
| Audit | No camelCase wire-field attribute access remains | R8 | development | `grep -rn "isError\|structuredContent\|inputSchema\|outputSchema" --include="*.py" server` | Zero hits (already true; this row exists to catch a regression, not to fix anything) |
| Audit | Same defect classes triaged for Rikyu, per R02's sibling-repo sweep | R1–R3 | development | This report's Risks table | Rikyu is marked fixed / not-applicable / deferred, each with a stated reason — satisfied by the table above, not by a new test |
| Live resources | `get_resources` performs the harness's first real SSH round trip (`sinfo`) | none (existing coverage, carried forward) | read-only (regression) | Live Rikyu SSH reachable | `payload(result)` includes the `gpu` partition |
| Contract, live | `get_job_statuses([])` is consumed via `payload()`; an empty result reads as an empty list, not a failure | R4 | read-only (regression) | Live Rikyu SSH; `job_ids=[]` against the accounting-enabled (`sacct`) backend | Call succeeds (`is_error is False`) whether the result is empty or not; no call site pipes the result through `json.loads` |
| Live command | `run_command_on_cluster('hostname')` succeeds | none (existing coverage, carried forward) | read-only (regression) | Live Rikyu SSH | `is_error is False`; returned hostname text is non-empty |
| Gating | `--job` alone (no second flag) refuses before constructing a client or touching SSH, naming the flag and the billing reason | none (this report's core trust-boundary deliverable) | `--job` (regression, no-SSH — runs every campaign, needs no cluster access) | Invoke with `--job` only, no cluster config required | Process exits non-zero; printed output names the second flag (`--confirm-billing`) and the word "billed"/"billing"; zero SSH/paramiko activity occurs |
| Gating | `--job --confirm-billing` submits a real job and reports it in the final summary | none | `--job` (integration `end_to_end`, operator-run only) | Live Rikyu SSH, both flags present, a throwaway `nvidia-smi` job | `submit_job` returns `is_error=False` and a job id; **never executed by this campaign or by CI** — the billing guardrail forbids it here |

## Fixtures / Test Data Strategy

- **Data needed:** a run-scoped token (e.g. a helper returning
  `f"rikyu-smoke-{os.getpid()}-{secrets.token_hex(4)}"`) threaded through the
  `--job` path's `JobSpec.name`; the existing 5-minute `nvidia-smi` job spec
  needs no change beyond that field. No container/`.sif` fixture is warranted
  (R3 is not-applicable — no container path exists to exercise).
- **Where it lives:** specs and the token helper stay inline in
  `server/tests/smoke.py`, same as today — small, readable, and doubling as a
  usage example, matching R02's own reasoning. No `server/tests/test_data/`
  directory is warranted for this scope.
- **Mock vs real strategy:** nothing here is mocked. The offline tier is real
  MCP stdio servers started against an absent/empty cluster config — a real
  code path exercised in a fake environment, not a fake server. The docs index
  is the real bundled index, not a copy. The read-only and `--job` tiers are
  real Slurm/SSH, per Trust boundaries above; `--job` is real but gated, and
  this campaign never flips the gate.

## Observability Requirements

- Every run — regardless of tier — ends with one machine-readable summary
  line reporting passed / failed / **skipped** counts. A skipped group is
  named in that line (e.g. `SKIPPED(job-tier: --confirm-billing not set)`),
  not silently folded into the passed count — the same distinction R02's own
  Coverage risk (R3) demands, generalized here since Rikyu's skip is the
  entire `--job` tier rather than one container check.
- The gating refusal (Gating, no-second-flag row) must print the flag name and
  the billing reason to stdout/stderr **before** the process exits, and must
  do so having made zero SSH-library calls — the refusal is the whole point,
  and it must be visible without reading source.
- `--job`'s hand-run nature (R7) is not solved by this campaign, only
  narrowed: the offline tier removes the *need* to run by hand for the
  coverage that matters for CI. When `--job` is run by an operator, its output
  should still be piped to a log file so a leaked job (R2, deferred) is
  diagnosable after the fact against a pre/post `squeue` snapshot — recorded
  here as a recommendation, not a Success Gate.

## Minimal Must-Run Regression Set

Ordered by cost; stop at the first failure.

1. **Offline tier** — `uv run --directory server python tests/smoke.py --offline`, no config, no network.
2. **Gating refusal** — `tests/smoke.py --job` (no `--confirm-billing`) exits non-zero, no SSH activity.
3. **Wire-field audit** — grep sweep for camelCase wire fields returns zero hits.
4. **Read-only tier** — `tests/smoke.py` (default) against live Rikyu.

`--job --confirm-billing` (real submission) is deliberately excluded from this
set — it is never a Success Gate for this campaign, per the billing guardrail.

## Scope Control Notes

- **Consolidations made:** the hpc-server and docs-server registration checks
  collapse into one parameterized offline row rather than two independent
  ones. R02's sibling-repo audit row (R1–R3, "marked fixed / not-applicable
  with a reason") is satisfied by this report's Risks table directly — it is
  not a new test to write, just this document itself.
- **Deliberately not tested:**
  - R1 (`update_job` privilege) — the harness never calls `update_job`; there
    is no behavior here to probe. If a future harness leaf adds `update_job`
    coverage, R02's privilege-adaptive probe-then-branch pattern is the one to
    replay.
  - R2 (job leak) — deferred, not fixed. A `try`/`finally` cleanup guard
    would be a real improvement, but adding one is out of this campaign's
    scope (see Out of scope) and is not proposed as a test here.
  - R3 (container self-skip) — no container coverage exists to self-skip.
  - R5 (poll-timeout ambiguity) — no poll loop exists in this harness.
- **Why 13 scenarios for what could look like a small refactor:** this is not
  one bug fix. R4/R8 are contract drift, R6 is a naming collision fix, R7 is
  closed by adding a whole new offline tier, and the `--job` gate is genuinely
  new trust-boundary surface (billed compute, no usage limit). The count sits
  at R02's own "new feature" characterization for the same reason R02 gave
  for its 11: the fix turns `--job` from a script into a gate.

## Handover Notes

- **Name the opt-in flag exactly `--confirm-billing`** (or an equally
  explicit synonym, chosen once and used consistently) across the refusal
  message, the `.claude/settings.json` `PreToolUse` matcher, and any
  documentation. A mismatch between the flag the code checks and the flag the
  message names would itself be a bug this report's Gating row cannot catch,
  since that row only asserts *a* flag is named, not that it is the real one.
- **`get_job_statuses([])`'s exact empty-vs-recent semantics were not
  verified against live Rikyu while writing this report** — this environment
  has no SSH access to Rikyu. Confirm the call actually returns an empty
  result on a quiet queue before relying on it as the R4 fixture; if it
  instead returns recent jobs regardless of the `job_ids` filter, substitute
  another call site that can legitimately return an empty list.
- **Do not "fix" R2 by adding a cleanup guard as part of this campaign.** It
  is a real gap and a fine target for a future leaf, but this campaign's
  Success Gates do not include it, and adding code that touches the `--job`
  path beyond gating/contract fixes risks scope creep into billable-compute
  territory this campaign is explicitly staying out of.
- **The stale `.pyc` files this leaf's background section warned about**
  (`server/tests/__pycache__/test_transport_*`, `test_ssh_helpers`, etc.) are
  not present in this worktree — `git ls-files server/tests` shows exactly one
  tracked file, `smoke.py`. Nothing to clean up; noted here only so the next
  reader isn't surprised the warning didn't reproduce.
