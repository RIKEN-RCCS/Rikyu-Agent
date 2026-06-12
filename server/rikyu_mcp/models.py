"""Data models mirroring the IRI Facility API schemas.

The IRI (Integrated Research Infrastructure) Facility API is the DOE
standard for programmatic facility access (see api.pdf / api.alcf.anl.gov).
Its compute schemas follow PSI/J: a JobSpec with ResourceSpec + JobAttributes,
and a normalized JobState. We implement a pragmatic subset; deviations are
noted in IRI_CHECKLIST.md at the repository root.
"""
from enum import Enum

from pydantic import BaseModel, Field


class JobState(str, Enum):
    """Normalized job states (IRI/PSI-J), mapped from Slurm native states."""
    QUEUED = "QUEUED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"
    UNKNOWN = "UNKNOWN"


_SLURM_STATE_MAP = {
    "PENDING": JobState.QUEUED,
    "CONFIGURING": JobState.QUEUED,
    "REQUEUED": JobState.QUEUED,
    "SUSPENDED": JobState.QUEUED,
    "RUNNING": JobState.ACTIVE,
    "COMPLETING": JobState.ACTIVE,
    "STAGE_OUT": JobState.ACTIVE,
    "COMPLETED": JobState.COMPLETED,
    "CANCELLED": JobState.CANCELED,
    "FAILED": JobState.FAILED,
    "TIMEOUT": JobState.FAILED,
    "OUT_OF_MEMORY": JobState.FAILED,
    "NODE_FAIL": JobState.FAILED,
    "BOOT_FAIL": JobState.FAILED,
    "DEADLINE": JobState.FAILED,
    "PREEMPTED": JobState.FAILED,
}


def map_slurm_state(native: str) -> JobState:
    # sacct reports e.g. "CANCELLED by 12345"
    return _SLURM_STATE_MAP.get(native.split()[0].rstrip("+"), JobState.UNKNOWN)


class ResourceSpec(BaseModel):
    """Resources for a job (PSI/J ResourceSpec subset).

    On AI4S the partition (JobAttributes.queue_name) fixes the per-node
    share; gpus_per_node is an AI4S-specific addition that maps to
    --gpus-per-node and must not exceed the partition's share.
    """
    node_count: int = 1
    processes_per_node: int = 1
    cpu_cores_per_process: int | None = None
    gpus_per_node: int = 1


class JobAttributes(BaseModel):
    """Scheduler attributes (PSI/J JobAttributes subset)."""
    duration: str = Field("01:00:00", description="Wall time, HH:MM:SS or D-HH:MM:SS")
    queue_name: str = Field("1n1gpu", description="Slurm partition")
    project_name: str | None = Field(None, description="Slurm account (not needed on AI4S)")
    custom_attributes: dict[str, str] = Field(default_factory=dict)


class JobSpec(BaseModel):
    """Job specification (PSI/J JobSpec subset).

    `executable` plus `arguments` form the command run inside the batch
    script; `executable` may be a shell line (e.g. 'module load nvhpc && srun ./app').
    """
    name: str = "rikyu-job"
    executable: str
    arguments: list[str] = Field(default_factory=list)
    directory: str | None = Field(None, description="Working directory for the job")
    environment: dict[str, str] = Field(default_factory=dict)
    stdout_path: str | None = None
    stderr_path: str | None = None
    resources: ResourceSpec = Field(default_factory=ResourceSpec)
    attributes: JobAttributes = Field(default_factory=JobAttributes)


class JobStatus(BaseModel):
    """Status record for one job (IRI JobStatus subset)."""
    job_id: str
    state: JobState
    native_state: str
    name: str = ""
    partition: str = ""
    elapsed: str = ""
    start_time: str = ""
    end_time: str = ""
    exit_code: str = ""
    nodes: str = ""
    workdir: str = ""
    reason: str = Field("", description="Why a queued job is waiting (from squeue)")
