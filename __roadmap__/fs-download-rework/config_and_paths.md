# Config download_dir + local path safety

**Goal**: Provide a configurable local download directory and a safe local-destination resolver, so `fs_download` can decide *where* on the agent's machine a file lands without the transfer code caring.
**Pre-conditions**:
- [ ] `server/` env resolves under `uv`
**Success Gates**:
- ⬜ `config.download_dir()` resolves `RIKYU_DOWNLOAD_DIR` → `local.download_dir` in config file → default, returning an absolute `Path` [run]
- ⬜ `resolve_local_dest(remote_path, local_path)` returns an absolute path, expands `~`, creates parent dirs, and rejects paths escaping the download dir when a sandbox root is configured [run]
- ⬜ New unit test exercises both helpers and passes under `uv run python -m pytest` [run]
**References**: [config.py](server/rikyu_mcp/config.py) — mirror the existing function-per-setting + env-precedence pattern (`ssh_host`, `embed_api_key`); [middleware.py §norm_path/quote_path](server/rikyu_mcp/middleware.py:22) — remote-side safety idiom to mirror locally.

## Step 1: Add download-dir + local path-safety helpers to config
**Goal**: Extend `config.py` with the local-destination policy, decoupled from any transport code.
**Implementation Logic**:
WHAT: (1) Add `download_dir() -> Path` resolving in order `RIKYU_DOWNLOAD_DIR` env → `local.download_dir` in `~/.rikyu/config.json` → a sensible default (`Path.cwd()`; do NOT hardcode `~/Downloads`). Return an absolute, expanded `Path`. (2) Add `resolve_local_dest(remote_path: str, local_path: str | None) -> Path`: when `local_path` is None, join `download_dir()` with `os.path.basename(remote_path)`; else expanduser+abspath `local_path` (if it is an existing dir or ends with `/`, treat as a directory and append the remote basename). Create the parent directory. If a sandbox root is configured (the `download_dir()` when `local.sandbox` is truthy), raise `ValueError` if the resolved path is not within it (use `Path.resolve()` + `is_relative_to`).
WHY: Keeps *where files land* as config policy in one place; `transfer.py` then only moves bytes between two concrete paths. Matches the repo's existing config idiom.
**Deliverables**: `server/rikyu_mcp/config.py` (new functions `download_dir`, `resolve_local_dest`); `server/tests/test_paths.py` (new; `test_download_dir_precedence`, `test_resolve_local_dest_basename`, `test_resolve_local_dest_sandbox_escape`).
**Consistency Checks**: `uv run python -m pytest server/tests/test_paths.py -q` (expected: PASS)
**Commit**: `feat(config): add download_dir and safe local-destination resolver`
