# Rikyu

An original, plain-language orientation to the RIKEN Supercomputer RIKYU,
written for users who drive it through RikyuAgent. It records the
site-specific facts that shape how you ask for work — not general HPC/Linux
background, and not a command reference. Stable facts (hardware shape, the
partition model, storage limits) are stated here so the agent can size a job
without a round-trip; genuinely changing values (queue occupancy, installed
Spack packages, your billing balance) are left to the live system, which the
agent queries on demand.

As of mid-2026 the system is in **Early Access Phase 2**, RIKYU's production
trial period (running through the end of September 2026) — expect some
policy details (billing, allocation rules) to still be settling.

## What Rikyu is

Rikyu is a GPU-first supercomputer at the RIKEN Center for Computational
Science: 400 compute nodes, each an NVIDIA GB200 NVL4 — 2 Grace CPUs (aarch64)
paired with 4 B200 GPUs, tied together by NVLink-C2C so the CPU and GPU share
a coherent memory space. Aggregate performance is about 64 PFLOPS at FP64 and
15.5 EFLOPS at FP8. Nodes are linked by an InfiniBand XDR fat-tree network;
jobs confined to one leaf switch's worth of nodes communicate fastest, while
jobs that span many nodes may cross spine switches and see more variable
latency under heavy simultaneous traffic.

The practical consequence: this is a GPU-first, aarch64 machine — describe
jobs in terms of GPUs, not CPU cores, and double-check that any prebuilt
binary, container, or Python wheel actually targets aarch64 (x86_64 builds
will not run).

## Getting on the system

Two ways in: the **Open OnDemand** web portal, or **SSH** to
`login.rikyu.r-ccs.riken.jp`. Either way you end up submitting jobs through
Slurm and reading/writing the same shared storage.

SSH access needs a registered public key — generate one locally (Ed25519 is
recommended; ECDSA P-521 or RSA ≥2048-bit also work) and register it through
Open OnDemand's "SSH Public Key" page before your first SSH login. There is no
password authentication.

An account requires applying through the RIKYU Account Application System
(RAAS); eligibility during Early Access Phase 2 is limited to ARiSE users,
accepted SPReAD1000 projects, and RIKEN members, and project representatives
must separately register the project and its members. Anyone continuing from
Early Access Phase 1 must re-apply — old accounts are kept only long enough to
migrate data by hand and cannot run jobs.

## Billing

Usage is billed by GPU-hour (300 yen/GPU-hour as of Early Access Phase 2,
consumption tax separate), billed in arrears as a lump sum after the phase
ends. There's a billing dashboard for checking current usage — ask the agent
to point you to it rather than tracking spend by hand.

## Running jobs

Rikyu schedules with Slurm and has a **single GPU partition**. You do not pick
a partition to get a certain number of GPUs — you ask for the GPU count
directly with `--gpus=N`, and Slurm places the job on however many nodes that
needs. Only specific counts are accepted: **1, 2, 3, or 4 GPUs** fit on a
single node; **8, 12, or 16** span 2, 3, or 4 nodes respectively (always 4
GPUs per node). Each GPU brings a fixed, proportional share of the node: 36
CPU cores and roughly 400 GB of combined CPU+GPU-addressable memory (GPU
memory itself is 173 GiB per GPU; the rest is CPU-side LPDDR5X, reachable from
the GPU over NVLink-C2C but with different performance characteristics —
don't assume the two are interchangeable for bandwidth-sensitive code).

Wall time is capped at 96 hours regardless of GPU count; have the agent
confirm the current default if you don't set one explicitly. Have the agent
submit through `sbatch`, check with `squeue`/`sacct`, and cancel with
`scancel` — you describe the job in resource terms and it handles the script.

## Storage

Three tiers, each with a different purpose and a real capacity limit:

- **Home** (`/home/<user>`) — 5 GB, Lustre, yours alone. Configuration and
  small scripts, not datasets.
- **Group** (`/data1/<group>`) — 1 TB per group, Lustre, shared read/write
  among everyone in that group. The right place for shared datasets and
  results; a single user may belong to more than one group.
- **Scratch** (`/tmp` on the compute node) — 1.5 TB per requested GPU, local
  xfs, visible only to the job that's running. Fast, but wiped the moment the
  job ends — copy anything worth keeping back to home or group storage before
  the job finishes.

Home and group storage sit on the same shared Lustre filesystem (2 PB
high-speed SSD backing home, 10 PB bulk HDD backing group), so both are
reachable from login nodes too, and both can request a capacity increase
through a support ticket if you outgrow the default.

## Software: modules and Spack

Two complementary systems, and it matters which one a piece of software comes
from:

- **Environment modules** (Lmod) give you the **NVIDIA HPC SDK** compiler
  toolchains: `nvhpc` (standard, includes MPI), `nvhpc-nompi` (bring your own
  MPI), `nvhpc-hpcx` (HPC-X MPI over InfiniBand), `nvhpc-hpcx-cuda13` (same,
  CUDA pinned to 13), and `nvhpc-byo-compiler` (use the system GCC instead of
  NVIDIA's compilers). Have the agent list current versions live rather than
  assuming one.
- **Spack** provides prebuilt **applications and libraries** — things like
  `quantum-espresso`, `gromacs`, `lammps`, plus a large catalogue of
  scientific Python, visualization, and dev tooling. Loading Spack's
  environment (`spack load <package>`) sets up `PATH` for that application;
  GPU-enabled builds exist for `petsc`, `lammps`, `quantum-espresso`,
  `gromacs`, and `kokkos`, and `quantum-espresso`/`gromacs` additionally have
  HPC-X-MPI-aware builds for multi-node runs. Requesting Spack GPU software
  does **not** by itself allocate GPUs — the Slurm `--gpus=` request still
  has to be made alongside it.

If a package you need isn't in the shared (public) Spack instance, you can
build your own in a private instance under your home directory and chain it
to the public one so you're not rebuilding shared dependencies from scratch —
have the agent walk you through this only when the public catalogue genuinely
doesn't cover what you need, since it's slower and more involved than using
what's already built.

## Bringing your own environment with containers

Singularity is available for carrying a specific software stack onto Rikyu.
Point the agent at a `.sif` image (built yourself or pulled from a registry)
and it runs your program inside it; GPU passthrough (`--nv`) is added
automatically whenever the job also requests GPUs.

## Following jobs and untangling failures

Ask the agent for a job's state, queue reason, and history rather than
memorizing Slurm's own state names — it normalizes them for you. Console
output lands in `slurm-<jobid>.out` in the job's working directory.

Common failure causes on Rikyu:

- An aarch64/x86_64 mismatch — a binary, container, or Python wheel built for
  x86_64 fails immediately with an "exec format" style error.
- Running out of the per-GPU memory share — request more GPUs (which scales
  both CPU and memory together) rather than only adding `--mem`.
- Hitting the 96-hour wall-time ceiling on a long run.
- Scratch data lost because it wasn't copied out of `/tmp` before the job
  ended.

## Staying current

Rikyu is in active early-access rollout, so partition rules, Spack packages,
and account/billing policy can all still change. The agent's live queries
(current queue state, installed Spack packages, module versions) are always
more current than anything written here — lean on those, and fall back to
RIKEN R-CCS support for anything this guide doesn't cover.
