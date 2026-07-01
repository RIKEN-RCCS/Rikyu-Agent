# rsync/scp portability probe

**Goal**: Record, on both the local machine and the remote cluster, which transfer tools exist and their versions/flavors — the deployment-constraint half of the benchmark report.
**Pre-conditions**:
- [ ] cluster reachable via `config.ssh_host()`
**Success Gates**:
- ⬜ Emits a JSON/dict report of: local `rsync` (all PATH entries + versions, flagging openrsync vs GNU and PATH-shadowing), local `scp`, local `ssh`; remote `rsync`/`scp` versions [run]
- ⬜ Flags whether `remotemanager` can construct a `Computer` (rsync ≥3.0 gate) under the *current* PATH [run]
- ⬜ Runnable against any configured host (rikyu/ai4s-r2, banyan, dgx1) via an arg [run]
**References**: earlier finding — local `/usr/bin/rsync` is openrsync 2.6.9 (shadows Homebrew `/opt/homebrew/bin/rsync` 3.4.4); remote is GNU rsync 3.2.5. remotemanager's gate is satisfied only when a ≥3.0 rsync is first on PATH.

## Step 1: Implement the portability probe
**Goal**: A small script that fingerprints the transfer environment on both ends.
**Implementation Logic**:
WHAT: New `server/tests/probe_portability.py` (CLI, `--host <alias>` default `config.ssh_host()`). Locally: `shutil.which`/`which -a` for `rsync`/`scp`/`ssh`, parse `--version`, classify each rsync as `openrsync` vs `GNU` and record PATH order (which wins). Attempt `remotemanager` `Computer` construction and record success/failure + message. Remotely (one `ssh <host>` round trip, tiny): `rsync --version; scp -V 2>&1 | head -1; uname -a`. Print a structured dict and also write `__reports__/fs-download-rework/portability.json`.
WHY: The benchmark's per-transport availability depends entirely on this (e.g. `rm_rsync` needs a ≥3.0 local rsync on PATH). Captures the openrsync/PATH gotcha as durable evidence for the port targets (banyan, dgx1).
**Deliverables**: `server/tests/probe_portability.py` (`probe_local`, `probe_remote`, `classify_rsync`, `main`); writes `__reports__/fs-download-rework/portability.json`.
**Consistency Checks**: `cd server && PATH="/opt/homebrew/bin:$PATH" uv run python tests/probe_portability.py --host ai4s-r2` (expected: PASS — prints report, no traceback)
**Commit**: `feat(bench): portability probe for local/remote transfer tooling`
