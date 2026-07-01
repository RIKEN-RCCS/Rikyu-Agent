# RemoteManager rsync wrapper

**Goal**: A transport that reuses RemoteManager's own rsync transport, bound to the same SSH URL the server already uses, to pull the file to disk.
**Pre-conditions**:
- [ ] `transfer.py` scaffold merged; `transports/` package exists
**Success Gates**:
- ⬜ Module registers transport name `"rm_rsync"` [run]
- ⬜ Constructing `rsync(url=get_frontend())` and building the pull queue works offline (no cluster) in a unit test [run]
- ⬜ Progress output is wrapped in `redirect_stdout(sys.stderr)` [static]
**References**: [middleware.py](server/rikyu_mcp/middleware.py) — `get_frontend()`; `remotemanager.transport.rsync` — `queue_for_pull(files, local, remote)` then `.transfer()`.

## Step 1: Implement the RemoteManager rsync transport as its own module
**Goal**: Self-contained module; do not edit `transfer.py` or `__init__.py`.
**Implementation Logic**:
WHAT: New file `server/rikyu_mcp/transports/t_remotemanager_rsync.py`. `from remotemanager.transport import rsync`, `from rikyu_mcp.transfer import register`, `from rikyu_mcp.middleware import get_frontend`. `@register("rm_rsync")` `def rm_rsync_transport(remote_path, local_dest):` → `t = rsync(url=get_frontend())`; `t.queue_for_pull(files=os.path.basename(remote_path), local=str(local_dest.parent), remote=os.path.dirname(remote_path) or ".")`; `with contextlib.redirect_stdout(sys.stderr): t.transfer(raise_errors=True)`. rsync lands `basename` in `local_dest.parent`; if that differs from `local_dest.name`, rename to `local_dest`. Remote dir is relative to the login home (matches server convention).
WHY: Maximum architectural consistency — reuses the exact transport layer already powering the server, with checksum on by default.
**Deliverables**: `server/rikyu_mcp/transports/t_remotemanager_rsync.py` (`rm_rsync_transport`, registered `"rm_rsync"`); `server/tests/test_transport_rm_rsync.py` (`test_rm_rsync_registered`, `test_build_pull_queue_offline` — constructs the transport + queues a pull without transferring, asserting no exception and the expected transfer pair).
**Consistency Checks**: `cd server && uv run python -m pytest tests/test_transport_rm_rsync.py -q` (expected: PASS)
**Commit**: `feat(transfer): add RemoteManager rsync download transport`
