# fs-download-rework — reports

Analysis artifacts for replacing base64-in-context `fs_download` with a
write-to-disk + metadata tool, and the transport benchmark behind the default.

## Round 00

- **[00-findings_v0.md](00-findings_v0.md)** ← latest — figure-first findings briefing; `decision-required: confirm` (rsync vs scp default).

## Raw data & figures

| Artifact | What |
|---|---|
| [benchmark.csv](benchmark.csv) / [benchmark.md](benchmark.md) | Wall-clock + integrity + token cost sweep (1K–100M × 4 transports, 10 reps) |
| [wallclock.png](wallclock.png) | Transport wall-clock vs size, mean ± min–max over 10 reps |
| [token_scaling.png](token_scaling.png) / [token_scaling.csv](token_scaling.csv) | base64-in-context token scaling law (tiktoken o200k_base) |
| [portability.json](portability.json) | Local/remote transfer-tooling probe (rsync/scp versions, PATH, remotemanager gate) |

## Status

Campaign implementation complete (see `__roadmap__/fs-download-rework/`). Open decision: default transport (`rsync` proposed; `scp` viable) — see the findings report's Steering Questions.
