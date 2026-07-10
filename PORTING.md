# Porting guide

This repo follows [hpc-agent-core's `PORTING.md`](https://github.com/william-dawson/hpc-agent-core/blob/main/PORTING.md)
for the general process (mental model, the no-write-access-to-core and
clarity-over-cleverness rules, machine-facts checklist, repo layout,
`config.py`/`compute.py` wiring, validation, and the standing invariants).

It is **not copied here** — a copy is a second place for it to go stale in,
which is exactly the mistake this guide itself warns against (an earlier
revision of this repo's own copy went stale within the same day it was
written). See [`AGENTS.md`](AGENTS.md) for what's specific to *this*
machine: RIKYU's cluster facts, decisions made under uncertainty while
porting, and the repo map.
