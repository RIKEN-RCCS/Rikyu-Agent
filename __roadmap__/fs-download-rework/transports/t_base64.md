# Enhanced base64 + local write

**Goal**: A `base64` transport that fetches a file as base64 over the SSH exec channel (bypassing the 200 KB truncation), decodes it in Python, and writes it to the local destination.
**Pre-conditions**:
- [ ] `transfer.py` scaffold merged (`register`, `run_capture` available)
- [ ] `rikyu_mcp/transports/` package with auto-discovery exists (main-thread glue)
**Success Gates**:
- ⬜ Module registers transport name `"base64"` [run]
- ⬜ Pure decode helper round-trips known base64 → bytes in a unit test [run]
- ⬜ Uses `transfer.run_capture` (full stdout), NOT `middleware.run_command` [static]
**References**: [transfer.py](server/rikyu_mcp/transfer.py) — `register`, `run_capture`; [middleware.py](server/rikyu_mcp/middleware.py) — `quote_path`.

## Step 1: Implement the base64 transport as its own module
**Goal**: Add a self-contained transport module; do not edit `transfer.py` or the package `__init__.py`.
**Implementation Logic**:
WHAT: New file `server/rikyu_mcp/transports/t_base64.py`. `from rikyu_mcp.transfer import register, run_capture` and `from rikyu_mcp.middleware import quote_path`. Define pure `_decode(b64_text: str) -> bytes` (just `base64.b64decode`). Define `@register("base64")` `def base64_transport(remote_path: str, local_dest: Path) -> None:` → `text = run_capture(f"base64 {quote_path(remote_path)}")`; `local_dest.write_bytes(_decode(text))`.
WHY: This is the honest version of today's tool — bytes go to *disk*, never the LLM context, and `run_capture` avoids the truncation bug that silently corrupts >146 KB files.
**Deliverables**: `server/rikyu_mcp/transports/t_base64.py` (`_decode`, `base64_transport`, registered as `"base64"`); `server/tests/test_transport_base64.py` (`test_base64_registered`, `test_decode_roundtrip`).
**Consistency Checks**: `cd server && uv run python -m pytest tests/test_transport_base64.py -q` (expected: PASS)
**Commit**: `feat(transfer): add base64 download transport`
