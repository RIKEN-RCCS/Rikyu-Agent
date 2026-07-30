# rikyu_mcp_sdk_v2 — reports

Rikyu's test-definition report for the plugin family's `mcp` 1.x → 2.0.0
migration: a per-risk triage of R02's eight-item risk set against Rikyu's
actual `server/tests/smoke.py`, and the three-tier smoke matrix
(`--offline` / read-only / `--job`) plus the `--job` billing-gate contract
for the `harness_and_gating` leaf to implement.

## Documents

### Round 00
- [00-test_definition_v0.md](00-test_definition_v0.md) — **(latest)**
  Risks table with a Rikyu verdict for R1–R8, Test Matrix across the three
  smoke tiers, fixtures strategy, observability requirements, minimal
  must-run regression set, and handover notes for the harness implementation.

## Status

- **Stage:** risk triage and tier specification complete. Not yet
  implemented — `harness_and_gating.md` owns the code change
  (`call()`/`payload()` helpers, the `--offline` flag, the two-flag `--job`
  gate); `validation/` owns running the read-only tier against live Rikyu.
- **Headline:** four of R02's eight risks transfer to Rikyu's simpler harness
  (R2 deferred by design, R4/R6/R7 apply); four do not (R1/R3/R5 have no
  matching code path here, R8 is already clean). This report is Rikyu's answer
  to R02's own sibling-repo audit row.
- **Next:** `harness_and_gating.md` implements the tiers and the
  `--confirm-billing` gate this report specifies; `validation/live_cluster.md`
  runs the read-only tier and `rikyu-doctor` against live Rikyu.
- **Related:** [R02 smoke `--job` test definition](../mcp_sdk_v2_migration/00-test_definition_v0.md) —
  the risk set this report triages · [R01 knowledge transfer](../mcp_sdk_v2_migration/00-knowledge_transfer_v0.md) —
  the `mcp` v2 client contract (`is_error`, `structured_content`) this
  report's R4 row and Contract rows cite · Octopus-Agent's
  `__reports__/octopus_port/` — the precedent this directory's shape follows.
