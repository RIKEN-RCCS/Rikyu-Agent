"""Tiered MCP stdio smoke harness for the RIKYU plugin — see PORTING.md §9.

    python tests/smoke.py --offline   # offline tier only: starts both
                                       # servers over stdio with no cluster
                                       # config required — tool
                                       # registration, the submit_job
                                       # schema, get_facility, and docs
                                       # search over the bundled index
    python tests/smoke.py             # offline tier, then the read-only
                                       # tier: adds SSH round trips against
                                       # live RIKYU (sinfo, sacct, hostname)
    python tests/smoke.py --job       # + submits a real 1-GPU job and
                                       # prints its job ID (does not wait
                                       # for it to finish or clean it up —
                                       # check on it and scancel/let it run
                                       # to completion yourself)

A passing run here (and a passing `python -m rikyu_mcp.doctor`) is not
proof the port works end to end against RIKYU's live scheduler — see
PORTING.md §9's warning. Run the read-only tier at least once, with real
RIKYU SSH access configured (~/.rikyu/config.json or RIKYU_HOST), before
considering a port change done; the offline tier alone only proves the tool
surface starts and registers correctly.

Every run ends with one summary line reporting passed/failed/skipped tier
counts; a skipped tier is named, not folded into the passed count.
"""
import argparse
import asyncio
import os
import secrets
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

_REQUIRED_HPC_TOOLS = {
    "get_facility", "get_resources", "get_resource", "get_drained_nodes",
    "submit_job", "get_job_status", "get_job_statuses", "cancel_job", "update_job",
    "run_command_on_cluster",
    "fs_ls", "fs_stat", "fs_view", "fs_head", "fs_tail", "fs_mkdir",
    "fs_upload", "fs_download", "fs_checksum", "fs_cp", "fs_mv",
    "fs_chmod", "fs_chown", "fs_symlink", "fs_compress", "fs_extract",
}
_REQUIRED_DOCS_TOOLS = {"search_docs", "list_doc_sections", "read_doc_section"}
_REQUIRED_SUBMIT_JOB_DEFS = {"Container", "JobAttributes", "ResourceSpec", "VolumeMount"}


# ---------------------------------------------------------------------------
# Result contract: read every call through is_error / structured_content.
# ---------------------------------------------------------------------------

async def call(session: ClientSession, name: str, args: dict | None = None):
    """Perform a tool call and assert it did not error.

    Raises with the server's own error text included, so the diagnosis is in
    the failure message rather than a separate log line.
    """
    result = await session.call_tool(name, args or {})
    if result.is_error:
        detail = "".join(getattr(block, "text", "") for block in result.content)
        raise AssertionError(f"{name} failed: {detail or '(server returned no error detail)'}")
    return result


def payload(result):
    """Return a tool result's actual value.

    Prefers `structured_content`; only falls back to the joined content-block
    text when it is absent (the MCP surface leaves it unset for return types
    it can't derive an output schema for, e.g. a bare `dict` annotation).
    Non-object return types are wire-wrapped as `{"result": ...}`; that
    wrapper is unwrapped here so an empty list reads as an empty list rather
    than as a truthy one-key dict, and nothing downstream ever hands an empty
    string to `json.loads`.
    """
    value = result.structured_content
    if value is not None:
        if isinstance(value, dict) and value.keys() == {"result"}:
            return value["result"]
        return value
    return "".join(getattr(block, "text", "") for block in result.content)


def job_name(prefix: str = "rikyu-smoke") -> str:
    """A run-scoped job name so two concurrent runs on RIKYU never collide."""
    return f"{prefix}-{os.getpid()}-{secrets.token_hex(4)}"


def check_job_name_isolation() -> None:
    first, second = job_name(), job_name()
    assert first != "rikyu-smoke-test" and second != "rikyu-smoke-test", (
        "job_name() must never return the fixed literal 'rikyu-smoke-test'"
    )
    assert first != second, "job_name() must be run-scoped, not constant across invocations"


# ---------------------------------------------------------------------------
# Docs server — read-only and needs no SSH in any tier.
# ---------------------------------------------------------------------------

async def check_docs_server() -> None:
    params = StdioServerParameters(command=sys.executable, args=["-m", "rikyu_mcp.docs_server"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = {t.name for t in tools.tools}
            missing = _REQUIRED_DOCS_TOOLS - names
            assert not missing, f"docs server missing tools: {missing}"
            print(f"[docs] {len(names)} tools registered")

            sections = await call(session, "list_doc_sections", {})
            section_str = str(payload(sections))
            assert section_str.strip(), "list_doc_sections returned nothing — was the docs index built?"
            print(f"[docs] list_doc_sections: {len(section_str.splitlines())} sections")

            results = await call(session, "search_docs", {"query": "gpu request slurm partition", "top_k": 2})
            assert str(payload(results)).strip(), "search_docs returned nothing"
            print("[docs] search_docs: OK")


# ---------------------------------------------------------------------------
# HPC server — split into what needs no SSH and what does.
# ---------------------------------------------------------------------------

async def check_hpc_server_offline(session: ClientSession) -> None:
    tools = await session.list_tools()
    names = {t.name for t in tools.tools}
    missing = _REQUIRED_HPC_TOOLS - names
    assert not missing, f"hpc server missing tools: {missing}"
    print(f"[hpc] {len(names)} tools registered")

    submit_job_tool = next(t for t in tools.tools if t.name == "submit_job")
    defs = set(submit_job_tool.input_schema.get("$defs", {}).keys())
    missing_defs = _REQUIRED_SUBMIT_JOB_DEFS - defs
    assert not missing_defs, f"submit_job input schema missing $defs: {missing_defs}"
    print(f"[hpc] submit_job schema $defs present: {sorted(defs)}")

    facility = await call(session, "get_facility", {})
    assert str(payload(facility)).strip(), "get_facility returned nothing"
    print("[hpc] get_facility: OK (no SSH required)")


async def check_hpc_server_live(session: ClientSession) -> None:
    # get_resources is a live sinfo query (not static config), so this is
    # the first real SSH round trip in this run, despite being grouped with
    # the facility checks in the offline tier above.
    resources = await call(session, "get_resources", {})
    resources_str = str(payload(resources))
    assert "gpu" in resources_str, "get_resources should list the 'gpu' partition"
    print(f"[hpc] get_resources (SSH + sinfo): {resources_str[:200]!r}")

    statuses = await call(session, "get_job_statuses", {"job_ids": []})
    print(f"[hpc] get_job_statuses([]) (SSH + sacct): {str(payload(statuses))[:200]!r}")

    hostname = await call(session, "run_command_on_cluster", {"command": "hostname"})
    print(f"[hpc] run_command_on_cluster('hostname') (SSH): {str(payload(hostname)).strip()!r}")


async def submit_smoke_job(session: ClientSession) -> None:
    spec = {
        "name": job_name(),
        "executable": "nvidia-smi",
        "resources": {"gpus": 1},
        "attributes": {"duration": "00:05:00"},
    }
    submitted = await call(session, "submit_job", {"spec": spec})
    print(f"[hpc] submit_job: {payload(submitted)}")
    print("[hpc] NOTE: this job is now queued/running on RIKYU — check its "
          "status and cancel it yourself if you don't want it to run to completion.")


# ---------------------------------------------------------------------------
# Tiers
# ---------------------------------------------------------------------------

async def _offline_tier() -> None:
    check_job_name_isolation()
    await check_docs_server()
    params = StdioServerParameters(command=sys.executable, args=["-m", "rikyu_mcp.hpc_server"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            await check_hpc_server_offline(session)


async def _read_only_tier() -> None:
    params = StdioServerParameters(command=sys.executable, args=["-m", "rikyu_mcp.hpc_server"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            await check_hpc_server_live(session)


async def _job_tier() -> None:
    params = StdioServerParameters(command=sys.executable, args=["-m", "rikyu_mcp.hpc_server"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            await submit_smoke_job(session)


# ---------------------------------------------------------------------------
# Observability: passed / failed / skipped, skips named, one summary line.
# ---------------------------------------------------------------------------

class Summary:
    def __init__(self) -> None:
        self.passed: list[str] = []
        self.failed: list[tuple[str, BaseException]] = []
        self.skipped: list[tuple[str, str]] = []

    def ok(self, tier: str) -> None:
        self.passed.append(tier)

    def fail(self, tier: str, exc: BaseException) -> None:
        self.failed.append((tier, exc))

    def skip(self, tier: str, reason: str) -> None:
        self.skipped.append((tier, reason))

    @property
    def all_passed(self) -> bool:
        return not self.failed

    def line(self) -> str:
        skipped_str = "; ".join(f"{tier} ({reason})" for tier, reason in self.skipped)
        out = f"SUMMARY passed={len(self.passed)} failed={len(self.failed)} skipped={len(self.skipped)}"
        if self.skipped:
            out += f" SKIPPED({skipped_str})"
        return out


async def _run_tier(summary: Summary, name: str, coro) -> None:
    try:
        await coro
        summary.ok(name)
        print(f"[{name}] tier: PASSED")
    except Exception as exc:
        summary.fail(name, exc)
        print(f"[{name}] tier: FAILED — {exc}", file=sys.stderr)


async def _run(args: argparse.Namespace, summary: Summary) -> None:
    await _run_tier(summary, "offline", _offline_tier())

    if args.offline:
        summary.skip("read-only", "--offline was requested; no live cluster contacted")
    elif not summary.all_passed:
        summary.skip("read-only", "offline tier failed")
    else:
        await _run_tier(summary, "read-only", _read_only_tier())

    if not args.job:
        summary.skip("job", "not requested; pass --job to submit and bill compute")
    elif not summary.all_passed:
        summary.skip("job", "an earlier tier failed")
    else:
        await _run_tier(summary, "job", _job_tier())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--offline", action="store_true",
                         help="Run only the offline tier: no SSH, no live cluster required.")
    parser.add_argument("--job", action="store_true",
                         help="Also submit a real 1-GPU job (nvidia-smi, 5 min wall time).")
    args = parser.parse_args()

    summary = Summary()
    asyncio.run(_run(args, summary))
    print(summary.line())
    return 0 if summary.all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
