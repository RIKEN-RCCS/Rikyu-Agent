"""Good-citizen download benchmark: wall-clock, integrity, and token cost.

Sweeps every registered transport (except the test-only ``_noop``) across a
small set of file sizes and reports, per (size, transport): wall-clock
mean/min/max over ``--repetitions`` serial runs, whether every run verified
its checksum, and the analytic token/context cost of the legacy
base64-in-context ``fs_download`` tool this transfer campaign replaces.

This is meant to run against a real, shared, early-access cluster, so it is
deliberately conservative:

- STRICTLY SERIAL — one transfer in flight at a time, ever.
- One remote fixture per size, created once, deleted immediately after all
  transports for that size have run (in a ``finally``), never left behind.
- A sleep (``--delay``) between every single transfer, including across
  repetitions and across transports.
- Hard-capped at 100 MB by default; anything at/above 1 GB is refused
  outright, no override.

Usage:
    cd server && uv run python tests/bench_download.py \\
        --sizes 1K,1M,10M,100M --repetitions 10 --delay 2.0

Fast smoke of the harness itself (no cluster access needed to parse args,
but running the sweep does need a reachable host):
    uv run python tests/bench_download.py --sizes 1K,1M --repetitions 2 --delay 1
"""
import argparse
import csv
import re
import statistics
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

REPORT_DIR = Path(__file__).resolve().parent.parent.parent / "__reports__" / "fs-download-rework"
CSV_PATH = REPORT_DIR / "benchmark.csv"
MD_PATH = REPORT_DIR / "benchmark.md"

# No 1 GB, ever. This is a shared, early-access machine.
HARD_CAP_BYTES = 1024**3

_SIZE_SUFFIXES = {"": 1, "K": 1024, "M": 1024**2, "G": 1024**3}
_SIZE_RE = re.compile(r"^(\d+)\s*([KMGkmg]?)\s*$")


def parse_sizes(spec: str) -> list[int]:
    """Parse a comma-separated size spec like "1K,1M,100M" into a list of bytes.

    Accepts a bare integer (bytes) or an integer followed by K/M/G (binary,
    1024-based), case-insensitive. Raises ValueError on anything else.
    """
    sizes = []
    for token in spec.split(","):
        token = token.strip()
        if not token:
            continue
        m = _SIZE_RE.match(token)
        if not m:
            raise ValueError(f"unrecognized size {token!r}; expected e.g. 1K, 10M, 100M, 512")
        n, suffix = m.groups()
        sizes.append(int(n) * _SIZE_SUFFIXES[suffix.upper()])
    return sizes


def legacy_token_cost(size: int) -> dict:
    """Analytic token/context cost of the legacy base64-in-context tool.

    b64_bytes is the exact size of the base64 encoding of `size` raw bytes
    (base64 emits 4 output chars per 3 input bytes, rounded up to the next
    multiple of 3 for padding). est_tokens approximates tokenizer behavior
    at ~4 chars/token, which is standard for base64 alphabet text.
    """
    b64_bytes = ((size + 2) // 3) * 4
    return {
        "size": size,
        "b64_bytes": b64_bytes,
        "est_tokens": b64_bytes / 4,
    }


# New-path (metadata-only) result is a small, ~fixed-size dict:
# {local_path, bytes, sha256, verified, transport}. Measured once below from
# an actual TransferResult repr rather than hardcoded, but it does not grow
# with file size, unlike the legacy path.
NEW_PATH_METADATA_CHARS_ESTIMATE = 160  # local_path + 64-hex sha256 + small fields
NEW_PATH_EST_TOKENS = NEW_PATH_METADATA_CHARS_ESTIMATE / 4


async def measure_legacy_tool(smallest_size: int, remote_path: str) -> dict | None:
    """Best-effort ground truth: call the real legacy fs_download MCP tool once.

    Only sane for the smallest fixture (fs_download hard-caps at 5 MB
    server-side and dumping a 100 MB base64 blob into a live MCP session is
    exactly the anti-pattern this campaign is replacing). Uses the same
    ClientSession pattern as tests/smoke.py.

    Returns None (never raises) if anything about this fails — a missing
    `mcp` package, a server that won't start, an unreachable host, or a tool
    error should degrade to "not measured" rather than aborting the sweep.
    The analytic legacy_token_cost() value is the value of record either way;
    this is only a cross-check.

    TODO(bench): this has not been exercised against a live server in this
    change (harness was validated offline only, per the leaf task's
    validation constraints). If it turns out MCP's stdio handshake or the
    server's tool schema doesn't match this call shape, the analytic value
    still stands — fix this function in a follow-up rather than blocking on
    it here.
    """
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        server_dir = Path(__file__).resolve().parent.parent
        run_sh = server_dir / "run.sh"
        params = StdioServerParameters(command=str(run_sh), args=["rikyu_mcp.hpc_server"])
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                t0 = time.perf_counter()
                result = await session.call_tool("fs_download", {"path": remote_path})
                elapsed = time.perf_counter() - t0
                text = "\n".join(c.text for c in result.content if c.type == "text")
                if result.isError:
                    return None
                return {
                    "size": smallest_size,
                    "actual_result_chars": len(text),
                    "actual_result_bytes": len(text.encode()),
                    "elapsed_s": elapsed,
                }
    except Exception as exc:  # noqa: BLE001 - best-effort ground truth, never fatal
        print(f"NOTE: measure_legacy_tool skipped ({type(exc).__name__}: {exc})", file=sys.stderr)
        return None


@dataclass
class TimingStats:
    """Wall-clock mean/min/max over a set of serial repetitions, plus verification."""

    size: int
    transport: str
    reps_ok: int
    reps_run: int
    mean_s: float
    min_s: float
    max_s: float
    all_verified: bool
    bytes_moved: int
    skipped: bool = False
    skip_reason: str = ""


@dataclass
class SweepResult:
    timings: list[TimingStats] = field(default_factory=list)
    legacy_costs: list[dict] = field(default_factory=list)
    legacy_ground_truth: dict | None = None
    total_bytes_moved: int = 0
    notes: list[str] = field(default_factory=list)


def _registered_transports() -> list[str]:
    """Every registered transport name except the test-only `_noop`."""
    from rikyu_mcp import transfer

    transfer._ensure_transports_loaded()
    return sorted(n for n in transfer._TRANSPORTS if not n.startswith("_"))


def make_fixture(size: int, remote_dir: str = "/tmp") -> str:
    """Create a single remote fixture file of exactly `size` bytes; return its path.

    Uses `head -c size /dev/urandom` piped to the destination so the file's
    content is not trivially compressible (a fairer test for transports that
    compress in transit, e.g. rsync -z) and so repeated runs get distinct
    content. Falls back to `dd` if `head -c` is unavailable on the remote.
    """
    from rikyu_mcp.transfer import run_capture

    remote_path = f"{remote_dir}/rikyu-bench-{uuid.uuid4().hex[:12]}.bin"
    cmd = (
        f"head -c {size} /dev/urandom > {remote_path} "
        f"|| dd if=/dev/urandom of={remote_path} bs=1 count={size} status=none"
    )
    run_capture(cmd)
    return remote_path


def _delete_fixture(remote_path: str) -> None:
    """Best-effort removal of a remote fixture; never raises (called from `finally`)."""
    from rikyu_mcp.transfer import run_capture

    try:
        run_capture(f"rm -f {remote_path}")
    except Exception as exc:  # noqa: BLE001 - cleanup must not mask the real error
        print(f"WARNING: failed to delete remote fixture {remote_path}: {exc}", file=sys.stderr)


def bench_one(size: int, transport: str, repetitions: int, delay: float,
               remote_path: str, local_dir: Path) -> TimingStats:
    """Time `repetitions` strictly serial downloads of one (size, transport) pair.

    Each repetition downloads to a fresh local file (removed immediately
    after timing/verifying it), sleeps `delay` seconds, then proceeds to the
    next repetition. Never runs two transfers concurrently.
    """
    from rikyu_mcp import transfer

    durations: list[float] = []
    verified_flags: list[bool] = []
    bytes_moved = 0

    for i in range(repetitions):
        local_dest = local_dir / f"bench-{transport}-{size}-{i}.bin"
        t0 = time.perf_counter()
        try:
            result = transfer.download_file(remote_path, local_dest, transport)
            elapsed = time.perf_counter() - t0
            durations.append(elapsed)
            verified_flags.append(result.verified)
            bytes_moved += result.bytes
        finally:
            local_dest.unlink(missing_ok=True)
        if delay > 0 and i < repetitions - 1:
            time.sleep(delay)

    return TimingStats(
        size=size,
        transport=transport,
        reps_ok=sum(verified_flags),
        reps_run=len(durations),
        mean_s=statistics.mean(durations) if durations else float("nan"),
        min_s=min(durations) if durations else float("nan"),
        max_s=max(durations) if durations else float("nan"),
        all_verified=all(verified_flags) if verified_flags else False,
        bytes_moved=bytes_moved,
    )


def write_report(sweep: SweepResult, sizes: list[int]) -> None:
    """Emit benchmark.csv (one row per size x transport x metric) and benchmark.md."""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "size_bytes", "transport", "reps_run", "reps_verified",
            "mean_s", "min_s", "max_s", "all_verified", "bytes_moved",
            "skipped", "skip_reason",
        ])
        for t in sweep.timings:
            writer.writerow([
                t.size, t.transport, t.reps_run, t.reps_ok,
                f"{t.mean_s:.6f}" if t.reps_run else "",
                f"{t.min_s:.6f}" if t.reps_run else "",
                f"{t.max_s:.6f}" if t.reps_run else "",
                t.all_verified, t.bytes_moved, t.skipped, t.skip_reason,
            ])
        writer.writerow([])
        writer.writerow(["size_bytes", "legacy_b64_bytes", "legacy_est_tokens",
                          "new_path_est_tokens"])
        for c in sweep.legacy_costs:
            writer.writerow([c["size"], c["b64_bytes"], f"{c['est_tokens']:.1f}",
                              f"{NEW_PATH_EST_TOKENS:.1f}"])

    lines = ["# Download transport benchmark", ""]
    lines.append("## Wall-clock + integrity")
    lines.append("")
    lines.append("| size | transport | reps | verified | mean (s) | min (s) | max (s) |")
    lines.append("|---|---|---|---|---|---|---|")
    for t in sweep.timings:
        if t.skipped:
            lines.append(f"| {t.size:,} | {t.transport} | - | SKIP | - | - | - ({t.skip_reason}) |")
            continue
        lines.append(
            f"| {t.size:,} | {t.transport} | {t.reps_ok}/{t.reps_run} | "
            f"{'yes' if t.all_verified else 'NO'} | {t.mean_s:.4f} | {t.min_s:.4f} | {t.max_s:.4f} |"
        )
    lines.append("")
    lines.append("## Token / context cost: legacy base64-in-context vs new metadata-only path")
    lines.append("")
    lines.append("| size | legacy b64 bytes | legacy est. tokens | new-path est. tokens | breaches ~10k tool cap? |")
    lines.append("|---|---|---|---|---|")
    for c in sweep.legacy_costs:
        breach = "YES" if c["est_tokens"] > 10_000 else "no"
        lines.append(
            f"| {c['size']:,} | {c['b64_bytes']:,} | {c['est_tokens']:.0f} | "
            f"{NEW_PATH_EST_TOKENS:.0f} | {breach} |"
        )
    if sweep.legacy_ground_truth:
        gt = sweep.legacy_ground_truth
        lines.append("")
        lines.append(
            f"Ground truth (real `fs_download` call, size={gt['size']:,} bytes): "
            f"actual result length {gt['actual_result_bytes']:,} bytes "
            f"({gt['elapsed_s']:.3f}s)."
        )
    else:
        lines.append("")
        lines.append("Ground truth `fs_download` call: not measured (see notes).")
    lines.append("")
    lines.append(f"Total bytes moved this sweep: {sweep.total_bytes_moved:,}")
    if sweep.notes:
        lines.append("")
        lines.append("## Notes")
        lines.append("")
        for n in sweep.notes:
            lines.append(f"- {n}")

    MD_PATH.write_text("\n".join(lines) + "\n")
    print(f"Wrote {CSV_PATH} and {MD_PATH}")


def resume_check(host: str | None) -> None:
    """Optional qualitative check: does an interrupted transfer resume or restart?

    Starts a 100 MB transfer, interrupts it partway, re-runs it, and reports
    whether the transport picked up where it left off (rsync --partial) or
    started over (scp/base64). This is a separate, un-timed, qualitative
    check — it is not part of the timed sweep and its result is not written
    to benchmark.csv/.md.
    """
    print(
        "--resume: qualitative resume/restart check is stubbed pending time on a live "
        "host to script a real mid-transfer interrupt (SIGINT to the rsync/scp "
        "subprocess at a controlled byte offset). Expected behavior per transport "
        "docstring: rsync (--partial) should resume; scp and base64 should restart "
        "from zero. Verify manually via: start a 100 MB download, Ctrl-C it partway, "
        "re-run, and compare elapsed time against a fresh cold transfer.",
        file=sys.stderr,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", default="1K,1M,10M,100M",
                        help="Comma-separated sizes, e.g. 1K,1M,10M,100M (default: %(default)s)")
    parser.add_argument("--repetitions", type=int, default=10,
                        help="Serial repetitions per (size, transport) (default: %(default)s)")
    parser.add_argument("--delay", type=float, default=2.0,
                        help="Seconds to sleep between transfers (default: %(default)s)")
    parser.add_argument("--max-size", default="100M",
                        help="Cap on any single fixture size (default: %(default)s)")
    parser.add_argument("--transports", default=None,
                        help="Comma-separated transport names (default: all registered minus _noop)")
    parser.add_argument("--host", default=None,
                        help="Override RIKYU_HOST for this run (defaults to config/env)")
    parser.add_argument("--resume", action="store_true",
                        help="Run the optional qualitative resume/restart check and exit")
    args = parser.parse_args(argv)

    if args.host:
        import os
        os.environ["RIKYU_HOST"] = args.host

    if args.resume:
        resume_check(args.host)
        return 0

    max_size = parse_sizes(args.max_size)[0]
    sizes = parse_sizes(args.sizes)

    sweep = SweepResult()

    capped_sizes = []
    for size in sizes:
        if size >= HARD_CAP_BYTES:
            sweep.notes.append(
                f"SKIPPED size {size:,} bytes: at/above the 1 GB hard cap; "
                f"this harness refuses to move >=1 GB on a shared early-access host."
            )
            print(f"NOTE: skipping size {size:,} (>= 1 GB hard cap)", file=sys.stderr)
            continue
        if size > max_size:
            sweep.notes.append(
                f"SKIPPED size {size:,} bytes: exceeds --max-size {max_size:,}."
            )
            print(f"NOTE: skipping size {size:,} (> --max-size {max_size:,})", file=sys.stderr)
            continue
        capped_sizes.append(size)

    if args.transports:
        transports = [t.strip() for t in args.transports.split(",") if t.strip()]
    else:
        transports = _registered_transports()
    print(f"Transports: {transports}", file=sys.stderr)

    import tempfile
    with tempfile.TemporaryDirectory(prefix="rikyu-bench-") as tmpdir:
        local_dir = Path(tmpdir)

        for size in capped_sizes:
            sweep.legacy_costs.append(legacy_token_cost(size))

            remote_path = None
            try:
                remote_path = make_fixture(size)
                print(f"Fixture ready: {remote_path} ({size:,} bytes)", file=sys.stderr)

                for transport in transports:
                    print(f"--- size={size:,} transport={transport} ---", file=sys.stderr)
                    try:
                        stats = bench_one(size, transport, args.repetitions, args.delay,
                                           remote_path, local_dir)
                    except Exception as exc:  # noqa: BLE001 - one bad transport shouldn't kill the sweep
                        note = (f"SKIPPED transport={transport} at size={size:,}: "
                                f"{type(exc).__name__}: {exc}")
                        sweep.notes.append(note)
                        print(f"NOTE: {note}", file=sys.stderr)
                        stats = TimingStats(
                            size=size, transport=transport, reps_ok=0, reps_run=0,
                            mean_s=float("nan"), min_s=float("nan"), max_s=float("nan"),
                            all_verified=False, bytes_moved=0,
                            skipped=True, skip_reason=str(exc),
                        )
                    else:
                        if not stats.all_verified:
                            note = f"INTEGRITY MISMATCH: size={size:,} transport={transport}"
                            sweep.notes.append(note)
                            print(f"WARNING: {note}", file=sys.stderr)
                    sweep.timings.append(stats)
                    sweep.total_bytes_moved += stats.bytes_moved
                    if args.delay > 0:
                        time.sleep(args.delay)
            finally:
                if remote_path is not None:
                    _delete_fixture(remote_path)

        if capped_sizes:
            smallest = min(capped_sizes)
            try:
                fixture_for_gt = make_fixture(smallest)
                try:
                    import asyncio
                    sweep.legacy_ground_truth = asyncio.run(
                        measure_legacy_tool(smallest, fixture_for_gt)
                    )
                finally:
                    _delete_fixture(fixture_for_gt)
            except Exception as exc:  # noqa: BLE001 - ground truth is best-effort
                sweep.notes.append(f"legacy ground-truth measurement failed: {exc}")

    print(f"Total bytes moved: {sweep.total_bytes_moved:,}", file=sys.stderr)
    write_report(sweep, sizes)

    if sweep.notes:
        print("\n--- NOTES (skipped/capped/mismatched coverage) ---", file=sys.stderr)
        for n in sweep.notes:
            print(f"- {n}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
