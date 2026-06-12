"""MCP server for the AI4S supercomputer, modeled on the IRI Facility API.

Tool groups mirror the IRI resource groups (facility, status, compute,
filesystem); each operation is executed on the AI4S login node over SSH via
remotemanager, since AI4S does not expose a REST facility API itself.
Coverage of the full API is tracked in IRI_CHECKLIST.md at the repo root.
"""
import shlex

from mcp.server.fastmcp import FastMCP

from rikyu_mcp import compute, config
from rikyu_mcp.middleware import run_command, write_remote_file
from rikyu_mcp.models import JobSpec, JobStatus
from rikyu_mcp.serving import serve

mcp = FastMCP("rikyu-hpc")

RESOURCE_ID = "ai4s"


def _check_resource(resource_id: str) -> None:
    if resource_id != RESOURCE_ID:
        raise ValueError(f"Unknown resource '{resource_id}'; this server manages '{RESOURCE_ID}'")


# === facility ================================================================

@mcp.tool()
def get_facility() -> dict:
    """Describe the AI4S facility: partitions, modules, storage, conventions.

    Static reference data (no SSH round-trip). On AI4S the partition name
    fixes the per-node resource share; jobs request GPUs with
    --gpus-per-node. (IRI: GET /facility)
    """
    return config.load_cluster_config()


# === status ==================================================================

@mcp.tool()
def get_resources() -> list[dict]:
    """List compute resources and their live state. (IRI: GET /status/resources)

    Returns the AI4S resource with a per-partition node-state summary
    (allocated/idle/other/total) from sinfo.
    """
    summary = run_command("sinfo --summarize --format='%P|%a|%l|%F'")
    partitions = []
    for line in summary.strip().splitlines():
        parts = line.split("|")
        if len(parts) != 4 or parts[0] == "PARTITION":
            continue
        alloc, idle, other, total = parts[3].split("/")
        partitions.append({
            "partition": parts[0].rstrip("*"),
            "available": parts[1],
            "time_limit": parts[2],
            "nodes": {"allocated": int(alloc), "idle": int(idle),
                      "other": int(other), "total": int(total)},
        })
    return [{
        "id": RESOURCE_ID,
        "type": "compute",
        "description": "RIKEN AI4S supercomputer (NVIDIA GB200, aarch64)",
        "partitions": partitions,
    }]


# === compute =================================================================

@mcp.tool()
def submit_job(spec: JobSpec, resource_id: str = RESOURCE_ID) -> dict:
    """Submit a job described by a JobSpec. (IRI: POST /compute/job/{resource_id})

    The spec is rendered as an sbatch script (kept under ~/.rikyu/jobs/ on
    the cluster for auditability) and submitted. Returns the job_id and the
    script path. AI4S notes: attributes.queue_name picks the partition,
    which fixes the per-node resource share; resources.gpus_per_node must
    not exceed that share; executable may be a shell line such as
    'module load nvhpc && srun ./app'.
    """
    _check_resource(resource_id)
    return compute.submit(spec)


@mcp.tool()
def get_job_status(job_id: str, resource_id: str = RESOURCE_ID) -> JobStatus:
    """Get the normalized status of one job. (IRI: GET /compute/status/...)

    state is the normalized IRI state (QUEUED/ACTIVE/COMPLETED/FAILED/
    CANCELED); native_state is Slurm's. For queued jobs, reason explains
    the wait. Job stdout defaults to <workdir>/slurm-<job_id>.out — read it
    with fs_tail or fs_view.
    """
    _check_resource(resource_id)
    statuses = compute.get_statuses([job_id])
    if not statuses:
        raise ValueError(f"Job {job_id} not found")
    return statuses[0]


@mcp.tool()
def get_job_statuses(job_ids: list[str], resource_id: str = RESOURCE_ID) -> list[JobStatus]:
    """Get statuses for several jobs at once, or recent jobs when job_ids is
    empty. (IRI: POST /compute/status/{resource_id})
    """
    _check_resource(resource_id)
    if job_ids:
        return compute.get_statuses(job_ids)
    # No IDs given: current user's jobs from the last two days.
    return compute.get_recent_statuses()


@mcp.tool()
def cancel_job(job_id: str, resource_id: str = RESOURCE_ID) -> JobStatus | str:
    """Cancel a queued or running job and report its resulting state.
    (IRI: DELETE /compute/cancel/{resource_id}/{job_id})
    """
    _check_resource(resource_id)
    return compute.cancel(job_id)


# === filesystem ==============================================================
# Paths are relative to the home directory unless absolute.

@mcp.tool()
def fs_ls(path: str = ".", show_hidden: bool = False) -> str:
    """List a directory on the cluster. (IRI: GET /filesystem/ls)"""
    flags = "-la" if show_hidden else "-l"
    return run_command(f"ls {flags} {shlex.quote(path)}")


@mcp.tool()
def fs_stat(path: str) -> str:
    """Stat a file or directory on the cluster. (IRI: GET /filesystem/stat)"""
    return run_command(f"stat {shlex.quote(path)}")


@mcp.tool()
def fs_view(path: str) -> str:
    """Read a whole text file on the cluster (output capped at 200KB).
    (IRI: GET /filesystem/view) For large files use fs_head/fs_tail.
    """
    return run_command(f"cat {shlex.quote(path)}")


@mcp.tool()
def fs_head(path: str, lines: int = 50) -> str:
    """Read the first lines of a file on the cluster. (IRI: GET /filesystem/head)"""
    return run_command(f"head -n {int(lines)} {shlex.quote(path)}")


@mcp.tool()
def fs_tail(path: str, lines: int = 50) -> str:
    """Read the last lines of a file on the cluster — e.g. a job's
    slurm-<job_id>.out. (IRI: GET /filesystem/tail)
    """
    return run_command(f"tail -n {int(lines)} {shlex.quote(path)}")


@mcp.tool()
def fs_mkdir(path: str) -> str:
    """Create a directory (and parents) on the cluster. (IRI: POST /filesystem/mkdir)"""
    quoted = shlex.quote(path)
    return run_command(f"mkdir -p {quoted} && echo created: $(realpath {quoted})")


@mcp.tool()
def fs_upload(path: str, content: str) -> str:
    """Write a text file on the cluster, creating parent directories.
    (IRI: POST /filesystem/upload)
    """
    abs_path = write_remote_file(path, content)
    return f"Wrote {len(content)} bytes to {abs_path}"


# === extensions (not part of the IRI API) ====================================

@mcp.tool()
def run_command_on_cluster(command: str) -> str:
    """Run an arbitrary shell command on the AI4S login node (extension —
    not an IRI endpoint).

    Use only when no dedicated tool fits, e.g. checking GPU usage on a
    job's node with 'srun --overlap --jobid <id> nvidia-smi'. Runs under a
    login shell from the home directory; returns stdout+stderr. Do not run
    heavy computation on the login node — submit a job instead.
    """
    return run_command(command)


def main():
    serve(mcp)


if __name__ == "__main__":
    main()
