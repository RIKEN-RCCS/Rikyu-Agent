# fs_download transport benchmark — findings & decision

## Why
`fs_download` returned a file's base64 **as the tool result**, routing bytes through the LLM context. Confirmed failure modes: (1) sub-5 MB files whose base64 exceeded the ~10k-token tool-output cap failed the call and inflated billing; (2) a silent >146 KB corruption bug (`run_command` truncates at 200 KB). We replace it with a host→local-disk transfer that returns metadata only, and benchmark four transports to choose the default.

## Method
Good-citizen sweep on Rikyu (`ai4s-r2`, early-access): sizes 1K/1M/10M/100M × {base64, rsync, scp, rm_rsync}, **10 reps, strictly serial, 3 s inter-transfer delay, remote fixtures deleted immediately**. 3.6 GB moved total. Every transfer checksum-verified. Raw data: [benchmark.csv](benchmark.csv), [benchmark.md](benchmark.md).

## Results — wall-clock mean (s)

| size | base64 | rsync | scp | rm_rsync |
|---|---|---|---|---|
| 1 KB | **1.62** | 1.90 | 1.97 | 1.99 |
| 1 MB | **2.29** | 2.70 | 2.59 | 2.70 |
| 10 MB | 6.83 | 5.83 | **5.65** | 9.25 |
| 100 MB | 52.74 | **39.61** | 53.77 | ✗ failed |

All runs `verified=True` (10/10) except rm_rsync@100 MB, which **failed** ("could not communicate with process").

## Token / context cost (the core motivation)

| size | legacy base64-in-context (est. tokens) | new metadata-only |
|---|---|---|
| 1 MB | ~349,500 | ~40 |
| 10 MB | ~3,495,000 | ~40 |
| 100 MB | ~34,950,000 | ~40 |

Ground truth: a real legacy `fs_download` of 1 KB returned 1,385 bytes (matches the analytic model). The new path returns a constant ~40-token metadata dict regardless of file size.

## Reading

- **Crossover ≈ 10 MB.** base64 wins for tiny files (one ssh round-trip, no handshake) but degrades as files grow (whole file streamed through Python memory). rsync/scp win at scale; **rsync is fastest at 100 MB** and brings `--partial` resume + `--checksum`.
- **rm_rsync is the weakest**: slowest at 10 MB, **failed at 100 MB**, and is the most fragile (blocked by `remotemanager`'s eager rsync≥3.0 gate on openrsync hosts; needed a fix for the SSH post-quantum stderr banner being misread as an error). Available, but not default.
- **scp** is a strong, universal alternative: present wherever OpenSSH is, competitive up to 10 MB, only modestly behind rsync at 100 MB; no delta/resume.

## Decision (for review — both defaults are defensible)

The transport is **configurable** (`local.download_transport` / `transport` arg), so the default is a one-line choice, not a code rewrite. Two reasonable defaults:

- **Option A (recommended) — default `rsync`**, fallback `rsync → scp → base64`. Best large-file speed, resume + checksum, portable (openrsync↔GNU interoperate).
- **Option B — default `scp`**, fallback `scp → rsync → base64`. Maximizes universality (OpenSSH everywhere) at a modest large-file speed cost.

`base64` is retained as the last-resort fallback (needs only `base64`+ssh; fine for the small files where it's actually fastest). `rm_rsync` remains available on request but out of the auto-fallback.

**Deployment note:** `remotemanager` (and `rm_rsync`) require rsync ≥3.0; enforce via the MCP server's env/PATH config (see the `deploy_rsync_env` change). The decoupled exec+checksum path keeps `base64`/`scp`/direct-`rsync` working even where that enforcement is absent.
