"""Live smoke test: drive both MCP servers over stdio, exactly as Claude Code does.

Usage:  python tests/smoke.py [--job]

Without --job: docs search + facility/status/queue queries (read-only).
With --job: additionally submits a tiny 5-minute test job via a JobSpec,
polls it to completion, and tails its output.
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER_DIR = Path(__file__).resolve().parent.parent
RUN_SH = SERVER_DIR / "run.sh"


async def call(session: ClientSession, tool: str, args: dict | None = None) -> str:
    result = await session.call_tool(tool, args or {})
    text = "\n".join(c.text for c in result.content if c.type == "text")
    status = "ERROR" if result.isError else "ok"
    print(f"--- {tool} [{status}] ---\n{text[:1200]}\n")
    if result.isError:
        raise RuntimeError(f"{tool} failed: {text}")
    return text


async def docs_checks() -> None:
    params = StdioServerParameters(command=str(RUN_SH), args=["rikyu_mcp.docs_server"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = [t.name for t in (await session.list_tools()).tools]
            print(f"rikyu-docs tools: {tools}\n")
            await call(session, "search_docs",
                       {"query": "how do I use local scratch storage", "top_k": 2})


async def hpc_checks(submit: bool) -> None:
    params = StdioServerParameters(command=str(RUN_SH), args=["rikyu_mcp.hpc_server"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = [t.name for t in (await session.list_tools()).tools]
            print(f"rikyu-hpc tools: {tools}\n")

            await call(session, "get_facility")
            await call(session, "get_resources")
            await call(session, "get_job_statuses", {"job_ids": []})

            if not submit:
                return

            spec = {
                "name": "rikyu-smoke",
                "executable": "hostname && nvidia-smi -L && echo scratch: $USER_SCRATCH_DIR",
                "attributes": {"duration": "00:05:00", "queue_name": "1n1gpu"},
                "resources": {"node_count": 1, "gpus_per_node": 1},
            }
            out = await call(session, "submit_job", {"spec": spec})
            job_id = json.loads(out)["job_id"]
            print(f">>> submitted job {job_id}; polling...\n")

            for _ in range(20):
                status_text = await call(session, "get_job_status", {"job_id": job_id})
                job = json.loads(status_text)
                state = job["status"]["state"]
                if state in ("completed", "failed", "canceled"):
                    break
                await asyncio.sleep(15)

            assert state == "completed", f"job ended {state}"
            workdir = job["status"]["meta_data"]["workdir"]
            await call(session, "fs_tail",
                       {"path": f"{workdir}/slurm-{job_id}.out", "lines": 20})


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", action="store_true",
                        help="Also submit and verify a tiny real job.")
    args = parser.parse_args()

    await docs_checks()
    await hpc_checks(submit=args.job)
    print("SMOKE TEST PASSED")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
