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
- **Estimated test volume and tiers:** 12 scenarios — 6 offline (regression),
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
