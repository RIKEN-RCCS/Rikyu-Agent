# Porting Guide: Implementing a New Machine

This guide is for an agent bootstrapping a new HPC MCP server from a clone of
this repository. Read it fully before writing any code.

The goal: a working MCP plugin for a new cluster that follows the same
architecture, passes `doctor.py`, and exposes the same tool surface as
`rikyu-hpc` (adapted to the target scheduler and filesystem).

---

## 1. Understand the architecture before touching anything

```
.claude-plugin/        plugin + marketplace manifests
.mcp.json              server launch config
server/rikyu_mcp/
  middleware.py        THE ONLY FILE THAT TALKS TO THE CLUSTER
  config.py            settings: env > file > defaults
  models.py            PSI/J-style schemas (JobSpec, Job, JobState, …)
  compute.py           scheduler translation layer (JobSpec → scripts)
  hpc_server.py        FastMCP tools, grouped by IRI API resource
  docs_server.py       docs RAG tools
  rag/                 embed / store / ingest
  doctor.py            health checks
  serving.py           shared CLI entry point
data/
  ai4s_config.json     static cluster facts (returned by get_facility)
  docs_index/          chunks.json + embeddings.npy
skills/                one SKILL.md per user-facing workflow
```

**What is generic (keep as-is):**
- `middleware.py` — SSH layer, base64 encoding, path handling, error raising.
  Only change the `Computer(...)` constructor args if the SSH setup differs.
- `models.py` — PSI/J shapes. Only deviate if the target scheduler has no
  equivalent concept (document any deviation in `IRI_CHECKLIST.md`).
- `rag/` — fully generic; change `EMBED_BASE_URL`/`EMBED_MODEL` in
  `config.py` if the embedding endpoint differs.
- `docs_server.py` — generic RAG tool surface; no changes needed.
- `serving.py` — no changes needed.

**What is machine-specific (must be replaced):**
- `config.py` — `ssh_host()` default, `EMBED_BASE_URL`, `EMBED_MODEL`,
  `DOCS_REPO_URL`, `DOCS_SITE_BASE`.
- `compute.py` — the scheduler translation layer (sbatch flags, sacct
  parsing). If the target uses PBS/LSF/SGE instead of Slurm, rewrite this
  file. The interface is: `render_script(spec) -> str`,
  `submit(spec) -> dict`, `get_statuses(ids) -> list[Job]`,
  `get_recent_statuses() -> list[Job]`, `cancel(job_id) -> Job | str`.
- `hpc_server.py` — the tool implementations that call scheduler commands.
  The IRI-grouped structure and tool names must be preserved; only the
  shell commands inside them change.
- `data/ai4s_config.json` — replace with the new machine's static facts.
- `data/docs_index/` — rebuild from the new machine's documentation.
- `skills/` — replace SKILL.md content with machine-specific workflows.
- `IRI_CHECKLIST.md` — update to track coverage for the new machine.

---

## 2. Non-negotiable design rules

Violating these will break things in non-obvious ways.

**All cluster I/O goes through `middleware.run_command` and
`middleware.write_remote_file`.** Never shell out to ssh directly from tool
code. The middleware enforces three invariants in one place:
1. Commands run under a **login shell** — schedulers resolve their
   environment through login profiles; a bare non-login shell will not find
   them.
2. The working directory is **$HOME** — relative paths resolve correctly,
   which is what users expect.
3. Payloads travel **base64-encoded** — this makes arbitrary quoting safe
   across the SSH layer.

**Use `quote_path()` for every remote path argument, never bare
`shlex.quote()`.** `shlex.quote("~/foo")` produces `'~/foo'`; single quotes
suppress tilde expansion in bash, so the shell looks for a literal directory
named `~`. `quote_path` calls `norm_path` first, stripping the `~/` prefix
(the CWD is already `$HOME`, so relative paths resolve there).

**Never write to stdout in server code.** The MCP stdio transport uses stdout
for JSON-RPC; any stray print corrupts the session. Write to stderr.
`remotemanager` prints progress to stdout; middleware redirects it.

**Error detection uses `result.returncode`, not stderr content.**
`raise_errors=False` disables remotemanager's built-in raise (which triggers
on non-empty stderr — too aggressive for commands that write benign messages
to stderr). Instead, `run_command` raises `RuntimeError` on any non-zero
exit code. FastMCP converts that to a clean MCP tool error. Callers never
need to parse error text from the return value.

**Tools are thin verbs; workflow knowledge belongs in `skills/`.**
A tool docstring should describe what it does, not when to use it or what
to do next. Long sequences of steps, retry logic, and "first do X then Y"
belong in SKILL.md files, not in docstrings.

**The IRI Facility API is the tool naming and grouping convention.**
Before adding, renaming, or removing a tool, check `IRI_CHECKLIST.md`.
Extensions with no IRI counterpart are allowed but must be marked as such
(e.g. `run_command_on_cluster`).

---

## 3. Phase 1 — Read the documentation

The user will have provided the machine's documentation (a local path or
repo). Read it fully before touching the cluster. The docs are the ground
truth for scheduler type, queue/partition names, GPU configuration, storage
layout, module system, and site-specific conventions. Build a mental model
from the docs first; SSH exploration is to fill gaps and verify, not to
discover from scratch.

While reading, extract answers to these questions and record them — they
become the static config JSON and inform everything that follows:

- What scheduler is used? (Slurm / PBS / LSF / other)
- What are the queue/partition names and their resource limits?
- How are GPUs requested?
- What are the storage tiers and their environment variable names?
- What container runtime is available (Singularity, Apptainer, pyxis)?
- What is the SSH hostname / alias convention?
- Are there project/account identifiers required for job submission?
- What modules are available and how is the module system loaded?

Fill in the static config JSON (`data/<machine>_config.json`) from the docs
before writing any tools. `get_facility` should return accurate data from
day one.

---

## 4. Phase 2 — Explore the machine

With the docs as context, use `run_command_on_cluster` to verify assumptions
and fill in anything the docs left ambiguous. Prefer targeted commands that
confirm specific facts over broad exploration.

**Confirm scheduler:**
```bash
which sbatch squeue sacct      # Slurm
which qsub qstat               # PBS/Torque
which bsub bjobs               # LSF
<scheduler> --version
```

**Job submission primitives:** submit a trivial job (`hostname`) and observe
the real output — this pins the exact format your parsers must handle:
- What does a successful submit print? (Slurm: `Submitted batch job <id>`)
- What does status/accounting output look like field by field?

**Filesystem:**
```bash
echo $HOME $SCRATCH              # confirm env var names
df -h                            # storage tiers
ls -la $HOME                     # home layout
```

**Container runtime:** if the docs mention a container runtime, probe it
on a compute node before committing to it in `compute.py`. On AI4S,
pyxis/enroot was documented as available but broken in practice
(`/run/user/<uid>` absent on compute nodes) — `singularity exec` worked.
Trust running experiments over documentation here.

---

## 5. Phase 3 — Adapt config and models

**`config.py`:**
- Change `ssh_host()` default to the new machine's SSH alias/hostname.
- Change `EMBED_BASE_URL` and `EMBED_MODEL` if a different embedding endpoint
  is used. If the same endpoint is used, only `embed_api_key()` needs user
  config.
- Change `DOCS_REPO_URL` and `DOCS_SITE_BASE` to the new machine's doc repo.
- Keep the env-var precedence chain: `RIKYU_HOST`, `RIKYU_EMBED_API_KEY`,
  `RIKYU_CONFIG`.

**`models.py`:**
The PSI/J shapes (`JobSpec`, `ResourceSpec`, `JobAttributes`, `JobState`)
are intentionally generic. Only deviate if the target scheduler has a concept
that genuinely cannot be mapped (e.g. PBS's `-l nodes=1:ppn=4` has no
direct IRI analogue). Document deviations in `IRI_CHECKLIST.md`.

`map_slurm_state()` must be replaced with `map_<scheduler>_state()` if not
Slurm. The normalized states are fixed: `QUEUED`, `ACTIVE`, `COMPLETED`,
`FAILED`, `CANCELED`, `HELD`, `UNKNOWN`.

---

## 6. Phase 4 — Implement the scheduler layer

**`compute.py`** is the only file that knows the scheduler dialect. Rewrite
it if needed, but keep the same interface:

| function | what it must do |
|---|---|
| `render_script(spec) -> str` | JobSpec → submission script string |
| `submit(spec) -> dict` | write script, submit, return `{job_id, script_path}` |
| `get_statuses(ids) -> list[Job]` | fetch normalized status for given IDs |
| `get_recent_statuses() -> list[Job]` | last N days for current user |
| `cancel(job_id) -> Job\|str` | cancel and return final state |

Scripts are written under `~/.rikyu/jobs/<name>-<timestamp>.sh` via
`write_remote_file` for auditability.

**Containers:** if the machine supports containers, prefer whatever mechanism
works reliably. On AI4S, `singularity exec` was chosen over pyxis/enroot
because `/run/user/<uid>` is absent on compute nodes. Probe before assuming.

**`hpc_server.py`:** the filesystem tools (`fs_ls`, `fs_stat`, `fs_view`,
etc.) are fully generic — they use standard POSIX commands and should need no
changes. The compute and status tools call into `compute.py` and are also
largely generic. The account tools (`get_projects`, `get_project`) are
scheduler-specific; rewrite the sacctmgr calls for the target system.

Test each tool with `run_command_on_cluster` first to see raw output, then
write the parser.

---

## 7. Phase 5 — Docs RAG

```bash
# clone the machine's doc repo into data/ or a temp dir
git clone --depth 1 <docs-repo-url> /tmp/newdocs

# run ingest (embedding endpoint must be configured)
python -m rikyu_mcp.rag.ingest --source /tmp/newdocs
```

`ingest.py` expects docs under `<source>/docs/en/*.md` (mkdocs layout).
If the doc repo has a different structure, adapt `build_index()` in
`ingest.py` — the chunking and URL logic is the only part that is
doc-repo-specific.

**Commit `embeddings.npy` and `chunks.json`** so the plugin works without a
network round-trip. The embedding model is locked to whatever was used at
ingest time — do not make it user-configurable. A user who changes the model
would get silently wrong cosine similarity results.

---

## 8. Phase 6 — Skills

Each skill is a `SKILL.md` that tells the agent *when* and *how* to use the
tools for a specific workflow. Port these four:

| skill | what it covers |
|---|---|
| `configuring` | first-time setup, SSH config, config.json |
| `submitting-jobs` | building a JobSpec, common patterns, container jobs |
| `monitoring-jobs` | polling, reading output, diagnosing failures |
| `ai4s-reference` | machine-specific quick reference (rename as needed) |

Replace AI4S-specific facts (partition names, GPU models, storage paths) with
the new machine's equivalents. Keep the structure.

---

## 9. Phase 7 — Validate

**`doctor.py`** runs all health checks in order:
1. Config file present and parseable
2. SSH reachable
3. Scheduler CLI responds
4. Embedding endpoint responds (dim check)
5. Docs index has chunks + embeddings

Extend `doctor.py` for any new checks the machine needs. All checks must
print `✓` or `✗` and return a bool. `main()` exits non-zero if any fail.

**Smoke tests** (`tests/smoke.py`): the read-only suite must pass without
a cluster allocation. The `--job` suite submits a real job; run it last and
only when everything else is green.

---

## 10. Common failure modes and fixes

| symptom | cause | fix |
|---|---|---|
| Scheduler commands not found | non-login shell | ensure `bash -l` in middleware template |
| `'~/foo'`: no such file | bare `shlex.quote` on a tilde path | use `quote_path()` |
| MCP session corrupts / JSON parse error | something printed to stdout | redirect to stderr |
| sbatch exits 0 but job never appears | script syntax error | check `~/.rikyu/jobs/` script manually |
| Vector search returns garbage | wrong model at query time | lock model as constant, never user-configurable |
| Tool always succeeds even when it fails | `raise_errors=False` without returncode check | check `result.returncode != 0` |
| Container job fails on compute node | pyxis/enroot needs `/run/user/<uid>` | use `singularity exec` instead |
| SSH times out mid-session | login shell profile is slow | profile the login shell; disable slow module init |
