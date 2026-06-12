# IRI Facility API coverage checklist

Tracks how far `rikyu-hpc` covers the [IRI Facility API](https://api.alcf.anl.gov/)
(ALCF implementation, captured in `api.pdf`). Each IRI endpoint maps to an MCP
tool executed on AI4S over SSH via remotemanager — there is no REST service;
we emulate the API's shape and semantics.

Legend: ✅ implemented · 🔜 planned next · ❌ deferred (with reason)

## facility

| IRI endpoint | Tool | Status | Notes |
|---|---|---|---|
| GET /facility | `get_facility` | ✅ | Static data from `data/ai4s_config.json` |
| GET /facility/sites | — | ❌ | Single-site deployment; fold into `get_facility` if ever needed |
| GET /facility/sites/{site_id} | — | ❌ | Same |

## status

| IRI endpoint | Tool | Status | Notes |
|---|---|---|---|
| GET /status/resources | `get_resources` | ✅ | One resource (`ai4s`) with per-partition node summary from sinfo |
| GET /status/resources/{resource_id} | — | 🔜 | Trivial filter over `get_resources`; add detailed view (per-node states, drain reasons via `sinfo -R`) |
| GET /status/incidents | — | ❌ | No incident data source on AI4S; closest signal is drained nodes / maintenance reservations (`scontrol show reservation`) |
| GET /status/incidents/{id} | — | ❌ | Same |
| GET /status/events | — | ❌ | Same |
| GET /status/events/{id} | — | ❌ | Same |

## account

| IRI endpoint | Tool | Status | Notes |
|---|---|---|---|
| GET /account/capabilities | — | ❌ | No equivalent concept exposed on AI4S |
| GET /account/projects | — | 🔜 | Map from `sacctmgr show associations user=$USER` (account `ea`) |
| GET /account/projects/{id} | — | 🔜 | Same source |
| GET .../project_allocations | — | ❌ | AI4S early access has no allocation accounting (`saldo`-like) yet |
| GET .../user_allocations | — | ❌ | Same |

## compute

| IRI endpoint | Tool | Status | Notes |
|---|---|---|---|
| POST /compute/job/{resource_id} | `submit_job` | ✅ | JobSpec → sbatch script (kept in `~/.rikyu/jobs/`); single SSH round trip |
| PUT /compute/job/{rid}/{job_id} | — | 🔜 | Map to `scontrol update job` (time limit, name); only valid pre-start for most fields |
| GET /compute/status/{rid}/{job_id} | `get_job_status` | ✅ | sacct + squeue Reason, normalized JobState |
| POST /compute/status/{rid} | `get_job_statuses` | ✅ | Batch; empty list = current user's last 2 days |
| DELETE /compute/cancel/{rid}/{job_id} | `cancel_job` | ✅ | scancel + post-cancel state report |

## filesystem

| IRI endpoint | Tool | Status | Notes |
|---|---|---|---|
| GET /filesystem/ls | `fs_ls` | ✅ | |
| GET /filesystem/stat | `fs_stat` | ✅ | |
| GET /filesystem/view | `fs_view` | ✅ | 200KB cap; text only |
| GET /filesystem/head | `fs_head` | ✅ | |
| GET /filesystem/tail | `fs_tail` | ✅ | Primary way to read job output |
| POST /filesystem/mkdir | `fs_mkdir` | ✅ | |
| POST /filesystem/upload | `fs_upload` | ✅ | Text content via MCP (no multipart); binary deferred |
| GET /filesystem/download | — | ❌ | Binary transfer doesn't fit MCP text content; revisit via remotemanager file transfer if needed |
| GET /filesystem/checksum | — | 🔜 | Trivial (`sha256sum`) |
| POST /filesystem/mv | — | 🔜 | Destructive-ish; add with confirmation guidance in skill |
| POST /filesystem/cp | — | 🔜 | Same |
| DELETE /filesystem/rm | — | ❌ | Deliberately omitted for now (destructive); agent can use the escape hatch with user confirmation |
| PUT /filesystem/chmod | — | ❌ | Low value for agent workflows |
| PUT /filesystem/chown | — | ❌ | Not permitted for normal users anyway |
| POST /filesystem/symlink | — | ❌ | Low value |
| POST /filesystem/compress | — | ❌ | Escape hatch covers it |
| POST /filesystem/extract | — | ❌ | Escape hatch covers it |

## task

| IRI endpoint | Tool | Status | Notes |
|---|---|---|---|
| GET /task/{task_id} | — | ❌ | IRI's async-task model exists because REST ops are queued; our SSH execution is synchronous, so there are no tasks to track. Revisit only if we add long-running server-side operations |
| DELETE /task/{task_id} | — | ❌ | Same |
| GET /task | — | ❌ | Same |

## Known deviations from the IRI/PSI-J schemas

- Schema fields were not expandable in the Swagger capture (`api.pdf`); our
  `JobSpec`/`ResourceSpec`/`JobAttributes`/`JobState` follow the PSI/J models
  the IRI compute API is built on. **Verify against `/openapi.json` when
  network access to api.alcf.anl.gov is available.**
- `ResourceSpec.gpus_per_node` is an AI4S-specific addition (maps to
  `--gpus-per-node`; PSI/J expresses GPUs as `gpu_cores_per_process`).
- `resource_id` is accepted (and validated) but there is a single resource, `ai4s`.
- `run_command_on_cluster` is an extension tool with no IRI counterpart.
- No auth layer: identity comes from the user's SSH key, not OAuth tokens.
