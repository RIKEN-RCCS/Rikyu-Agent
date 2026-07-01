# Base64 token-scaling-law experiment (local, tokenizer)

**Goal**: Empirically measure how the token cost of base64-in-context grows with file size, using a real tokenizer as proxy, and plot the scaling law.
**Pre-conditions**:
- [x] no cluster needed — fully local
**Success Gates**:
- ⬜ Script tokenizes base64 of random bytes across log-spaced sizes with a real tokenizer (tiktoken proxy) and writes a CSV [run]
- ⬜ Plot: x = file size bytes (log scale), y = tokens, with the analytic chars/4 reference line and the ~10k-token tool-output cap annotated [run]
- ⬜ Reports the file size at which base64-in-context breaches the ~10k-token cap [run]
**References**: benchmark token table (analytic chars/4 estimate) — this validates it against a real tokenizer.

## Step 1: Implement the token-scaling experiment + plot
**Goal**: A local script producing the scaling-law data + figure.
**Implementation Logic**:
WHAT: New `server/tests/token_scaling.py`. For log-spaced sizes (e.g. 64 B → ~8 MB, ~24 points): generate random bytes, base64-encode, count tokens with `tiktoken` (o200k_base — modern GPT-4o encoding, a reasonable cross-LLM proxy for BPE token cost of ASCII), also record the analytic `ceil(bytes/3)*4/4` estimate. Write `__reports__/fs-download-rework/token_scaling.csv` and render `token_scaling.png` (matplotlib): x=file bytes on a log scale, y=tokens; plot the measured-tokenizer series and the analytic reference; draw a horizontal line at 10,000 tokens (typical tool-output cap) and annotate the crossover file size. Fit and report the linear slope (tokens per byte) — base64-in-context is ~O(n), which on a log-x axis rises steeply, making the point visually. Keep it deterministic (seed the RNG via a fixed byte pattern, not Random) so re-runs match.
WHY: Turns the "≈349k tokens at 1 MB" analytic claim into an empirical, tokenizer-grounded scaling law — a compelling single figure showing base64-in-context is fundamentally unviable past a few KB.
**Deliverables**: `server/tests/token_scaling.py` (`measure`, `plot`, `main`); outputs `__reports__/fs-download-rework/token_scaling.csv` + `token_scaling.png`.
**Consistency Checks**: `cd server && uv run python tests/token_scaling.py` (expected: PASS — writes CSV + PNG, prints the 10k-cap crossover size)
**Commit**: `feat(bench): base64 token-scaling-law experiment + plot`
