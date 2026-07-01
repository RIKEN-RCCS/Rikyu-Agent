# Enforce rsync>=3.0 at deploy via MCP env/PATH config

**Goal**: Guarantee a rsync ≥3.0 is on PATH when the MCP server runs, so `remotemanager` (hence `rm_rsync` and the whole `run_command` path) works — enforced through MCP-host env/PATH configuration, not code.
**Pre-conditions**:
- [ ] decouple_ssh_helpers merged (our download path already survives without this; this restores the rest of the server)
**Success Gates**:
- ⬜ README/configuring docs state the rsync ≥3.0 requirement and show how to set PATH in the MCP server config (e.g. `env`/`PATH` in the MCP host's server entry) [static]
- ⬜ A documented example prepends a modern rsync (e.g. `/opt/homebrew/bin` on macOS) ahead of `/usr/bin` [static]
- ⬜ `rikyu-doctor`'s rsync-gate failure message is actionable — it names the fix (put rsync ≥3.0 first on PATH via MCP env config) rather than only reporting the version error [run]
**References**: [doctor.py](server/rikyu_mcp/doctor.py) — the ssh check that surfaces the remotemanager rsync-gate error; [README.md](README.md) / configuring skill — where deployment/config guidance lives; earlier finding — macOS ships openrsync 2.6.9 at `/usr/bin/rsync`, shadowing Homebrew rsync 3.4.4 at `/opt/homebrew/bin/rsync`.

## Step 1: Document + guide the rsync>=3.0 deployment requirement
**Goal**: Make the requirement explicit and self-service, and make the failure actionable.
**Implementation Logic**:
WHAT: (1) Add a short "Requirements: rsync ≥3.0 on PATH" section to the deployment docs (README and/or the configuring skill), explaining remotemanager needs it and how to guarantee it by setting `PATH` (or a wrapper) in the MCP server's launch config in the host — with a macOS example prepending `/opt/homebrew/bin`. (2) Improve `doctor.py`'s ssh-check handling so that when the rsync-version RuntimeError is caught, the printed guidance names the concrete remedy (install rsync ≥3.0 and put it first on PATH via the MCP server env config), linking the transport-change docs. Keep it a soft, actionable message. No change to the transfer code (that was the decouple leaf).
WHY: remotemanager expects rsync ≥3.0 and that is a reasonable requirement to keep; the right place to satisfy it is deployment configuration (env/PATH in the MCP host), which is easy in modern MCP hosts. The decoupling already keeps downloads working; this restores `rm_rsync` and every other `fs_*`/job tool that rides `run_command`.
**Deliverables**: `README.md` (or configuring skill doc) — "rsync ≥3.0 / PATH" section with an MCP-config env example; `server/rikyu_mcp/doctor.py` — actionable rsync-gate guidance.
**Consistency Checks**: `cd server && uv run rikyu-doctor` (expected: with a ≥3.0 rsync first on PATH the ssh check passes; without it, the failure message now names the PATH/env remedy)
**Commit**: `docs(deploy): require rsync>=3.0 on PATH via MCP env config; actionable doctor hint`
