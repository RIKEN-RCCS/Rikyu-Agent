# Benchmark plots + writing-reports findings artifact

**Goal**: Turn the raw sweep + token-scaling data into professional plots and a `writing-reports` findings artifact that anchors the PR.
**Pre-conditions**:
- [ ] token_scaling done (its figure is embedded here)
- [x] benchmark.csv present
**Success Gates**:
- ⬜ Wall-clock plot: mean per transport vs file size with **min–max error bars over the 10 reps** (log axes), one series per transport [run]
- ⬜ Findings report at `__reports__/fs-download-rework/00-findings_v0.md` follows the writing-reports findings format (front matter, Headline, Results Tables, Observations, Charts, Steering Questions, Pointers) and embeds the PNGs [static]
- ⬜ Topic `README.md` indexing the report + artifacts [static]
**References**: [writing-reports findings format](~/.claude/skills/writing-reports/references/findings.md); [benchmark.csv](__reports__/fs-download-rework/benchmark.csv); token_scaling outputs.

## Step 1: Plot the wall-clock landscape
**Goal**: Render the transport wall-clock comparison with error bars.
**Implementation Logic**:
WHAT: New `server/tests/plot_benchmark.py` reading `benchmark.csv`: for each transport, plot mean wall-clock vs file size on log-log axes with asymmetric error bars `[mean-min, max-mean]` (the full spread of the 10 reps — no stat test, this is a landscape). Mark the rm_rsync@100 MB failure. One-line caption, labeled axes+units. Save `__reports__/fs-download-rework/wallclock.png`.
WHY: The crossover (base64 best small, rsync/scp best large) and rm_rsync's blow-up are far clearer as a figure than a table.
**Deliverables**: `server/tests/plot_benchmark.py` (`load`, `plot_wallclock`, `main`); outputs `wallclock.png`.
**Consistency Checks**: `cd server && uv run python tests/plot_benchmark.py` (expected: PASS — writes wallclock.png)
**Commit**: `feat(bench): wall-clock landscape plot with min-max error bars`

## Step 2: Assemble the writing-reports findings artifact
**Goal**: Author the canonical findings report embedding both figures.
**Implementation Logic**:
WHAT: Create `__reports__/fs-download-rework/00-findings_v0.md` per the findings format: front matter (`decision-required: confirm` — the rsync-vs-scp default), Headline Result (token cost collapse), Results Tables (wall-clock + token cost), Observations (Signal/Baseline/Observed/Interpretation), Charts embedding `wallclock.png` + `token_scaling.png`, Steering Questions (default choice, fs_upload follow-up), Pointers (csv/probe/roadmap). Add `__reports__/fs-download-rework/README.md` indexing artifacts by round. Supersede the ad-hoc `findings.md` (fold its content in, then remove it).
WHY: Gives the PR a stakeholder-grade, figure-first artifact instead of an ad-hoc note.
**Deliverables**: `__reports__/fs-download-rework/00-findings_v0.md`; `__reports__/fs-download-rework/README.md`; remove `findings.md`.
**Consistency Checks**: `test -s __reports__/fs-download-rework/00-findings_v0.md && test -f __reports__/fs-download-rework/wallclock.png` (expected: PASS)
**Commit**: `docs(bench): writing-reports findings artifact with figures`
