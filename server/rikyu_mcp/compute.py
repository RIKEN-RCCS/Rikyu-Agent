"""JobSpec → Slurm translation and status parsing (IRI compute backend)."""
import shlex
import time

from rikyu_mcp.middleware import run_command, write_remote_file
from rikyu_mcp.models import JobSpec, JobStatus, map_slurm_state

_SACCT_FIELDS = "JobID,JobName,Partition,State,Elapsed,Start,End,ExitCode,NodeList,WorkDir"


def render_script(spec: JobSpec) -> str:
    """Render a JobSpec as an AI4S sbatch script."""
    lines = [
        "#!/bin/bash",
        f"#SBATCH --job-name={spec.name}",
        f"#SBATCH --partition={spec.attributes.queue_name}",
        f"#SBATCH --nodes={spec.resources.node_count}",
        f"#SBATCH --gpus-per-node={spec.resources.gpus_per_node}",
        f"#SBATCH --ntasks-per-node={spec.resources.processes_per_node}",
        f"#SBATCH --time={spec.attributes.duration}",
    ]
    if spec.resources.cpu_cores_per_process:
        lines.append(f"#SBATCH --cpus-per-task={spec.resources.cpu_cores_per_process}")
    if spec.attributes.project_name:
        lines.append(f"#SBATCH --account={spec.attributes.project_name}")
    if spec.directory:
        lines.append(f"#SBATCH --chdir={spec.directory}")
    if spec.stdout_path:
        lines.append(f"#SBATCH --output={spec.stdout_path}")
    if spec.stderr_path:
        lines.append(f"#SBATCH --error={spec.stderr_path}")
    lines.append("")
    for key, value in spec.environment.items():
        lines.append(f"export {key}={shlex.quote(value)}")
    command = spec.executable
    if spec.arguments:
        command += " " + " ".join(shlex.quote(a) for a in spec.arguments)
    lines.append(command)
    lines.append("")
    return "\n".join(lines)


def submit(spec: JobSpec) -> dict:
    """Write the rendered script on the cluster and sbatch it.

    The script is kept under ~/.rikyu/jobs/ for auditability.
    """
    stamp = time.strftime("%Y%m%d-%H%M%S")
    script_path = write_remote_file(
        f".rikyu/jobs/{spec.name}-{stamp}.sh", render_script(spec)
    )
    output = run_command(f"sbatch --parsable {shlex.quote(script_path)}")
    # --parsable prints "<job_id>" or "<job_id>;<cluster>"
    job_id = output.strip().splitlines()[-1].split(";")[0] if output.strip() else ""
    if not job_id.isdigit():
        raise RuntimeError(f"sbatch failed: {output}")
    return {"job_id": job_id, "script_path": script_path}


def _parse_sacct(output: str) -> list[JobStatus]:
    statuses = []
    for line in output.strip().splitlines():
        parts = line.split("|")
        if len(parts) < 10 or parts[0] == "JobID":
            continue
        if "." in parts[0]:  # skip job steps (e.g. 15614.batch)
            continue
        statuses.append(JobStatus(
            job_id=parts[0],
            state=map_slurm_state(parts[3]),
            native_state=parts[3],
            name=parts[1],
            partition=parts[2],
            elapsed=parts[4],
            start_time=parts[5],
            end_time=parts[6],
            exit_code=parts[7],
            nodes=parts[8],
            workdir=parts[9],
        ))
    return statuses


def _attach_reasons(statuses: list[JobStatus]) -> list[JobStatus]:
    """For queued jobs, attach the squeue wait reason."""
    queued = [s for s in statuses if s.state == "QUEUED"]
    if not queued:
        return statuses
    ids = ",".join(s.job_id for s in queued)
    output = run_command(f"squeue --jobs={ids} --format='%i|%R' --noheader")
    reasons = dict(
        line.split("|", 1) for line in output.strip().splitlines() if "|" in line
    )
    for status in statuses:
        status.reason = reasons.get(status.job_id, "").strip()
    return statuses


def get_statuses(job_ids: list[str]) -> list[JobStatus]:
    """Fetch normalized statuses for one or more jobs."""
    ids = ",".join(shlex.quote(j) for j in job_ids)
    output = run_command(
        f"sacct --jobs={ids} --format={_SACCT_FIELDS} --parsable2 --noheader"
    )
    return _attach_reasons(_parse_sacct(output))


def get_recent_statuses(since: str = "now-2days") -> list[JobStatus]:
    """Statuses of the current user's jobs since the given time."""
    output = run_command(
        f"sacct --starttime={shlex.quote(since)} --format={_SACCT_FIELDS} "
        f"--parsable2 --noheader"
    )
    return _attach_reasons(_parse_sacct(output))


def cancel(job_id: str) -> JobStatus | str:
    """scancel, then report the job's state."""
    run_command(f"scancel {shlex.quote(job_id)}")
    statuses = get_statuses([job_id])
    return statuses[0] if statuses else f"scancel sent; job {job_id} not found in sacct"
