# Update smoke.py, IRI_CHECKLIST, docstrings

**Goal**: Bring tests and docs in line with the new `fs_download` contract and record the deliberate IRI deviation.
**Pre-conditions**:
- [ ] rewrite_tool done — `fs_download` returns metadata
**Success Gates**:
- ⬜ `smoke.py`'s fs_download step asserts the metadata dict + local file exists + checksum matches `fs_checksum` (no more base64-decode of the result) [run, live]
- ⬜ `IRI_CHECKLIST.md` marks GET /filesystem/download as a deliberate deviation with rationale (token cap, billing, truncation bug) [static]
- ⬜ README/tool docstring describe the write-to-disk + metadata behavior and the `local_path`/`transport` args [static]
**References**: [smoke.py:61](server/tests/smoke.py:61) — current base64-decode assertion; [IRI_CHECKLIST.md:59](IRI_CHECKLIST.md:59) — the download row; [README.md](README.md) — tool docs.

## Step 1: Align tests + docs with the new contract
**Goal**: Make the smoke test and docs reflect metadata-only downloads.
**Implementation Logic**:
WHAT: (1) In `smoke.py`, change the `fs_download` step: call it (optionally with a `local_path` under a temp dir), parse the returned metadata, assert the local file exists, its size matches, and its sha256 equals `fs_checksum` of the remote — drop the `base64.b64decode(result)` assertion. Add a case with a >146 KB file to prove the old truncation path is gone. (2) In `IRI_CHECKLIST.md`, update the `GET /filesystem/download` row to "deviation" with a one-line rationale and a pointer to this campaign. (3) Update the `fs_download` docstring/README to document write-to-disk, the metadata return shape, and the `local_path`/`transport` parameters; note the rsync≥3.0 deploy requirement cross-link (deploy_rsync_env).
WHY: Tests and docs must match the new behavior, and the IRI deviation must be explicit so future collaborators understand why we diverge from the spec's base64 shape.
**Deliverables**: `server/tests/smoke.py` (updated fs_download assertions + >146 KB case); `IRI_CHECKLIST.md` (download row → deviation + rationale); `README.md` and/or the `fs_download` docstring (new contract documented).
**Consistency Checks**: `cd server && PATH="/opt/homebrew/bin:$PATH" uv run python tests/smoke.py` (expected: PASS — fs_download step verifies the local file + checksum)
**Commit**: `docs(fs): align smoke test + IRI checklist + docs with metadata download`
