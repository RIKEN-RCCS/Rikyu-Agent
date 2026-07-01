"""Empirical token-scaling law for base64-in-context downloads.

The old fs_download returned a file's base64 *as the tool result*, so the model
paid tokens proportional to file size. This measures that cost with a real
tokenizer (tiktoken o200k_base — GPT-4o's encoding, a reasonable cross-LLM
proxy for the BPE token cost of ASCII) across log-spaced file sizes, and plots
the scaling law against the ~10k-token tool-output cap.

    cd server && uv run python tests/token_scaling.py

Writes __reports__/fs-download-rework/token_scaling.{csv,png}. Deterministic
(fixed byte pattern, no RNG) so re-runs reproduce.
"""
import base64
import csv
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt
import tiktoken

REPORT_DIR = Path(__file__).resolve().parents[2] / "__reports__" / "fs-download-rework"
TOOL_TOKEN_CAP = 10_000  # typical per-tool-output token ceiling for an agent

# Log-spaced sizes from 64 B to 8 MiB.
SIZES = [int(64 * (2 ** (i / 2))) for i in range(0, 35)]  # 64 B .. ~8 MB


def _payload(n: int) -> bytes:
    """A deterministic, high-entropy-ish n-byte payload (no RNG, reproducible)."""
    # A repeating 256-byte cycle: not compressible into a few tokens the way
    # all-zeros would be, but fully deterministic.
    pattern = bytes(range(256))
    reps = n // 256 + 1
    return (pattern * reps)[:n]


def measure() -> list[dict]:
    """Token count of base64(payload) per size, real tokenizer vs analytic."""
    enc = tiktoken.get_encoding("o200k_base")
    rows = []
    for n in SIZES:
        b64 = base64.b64encode(_payload(n)).decode()
        tokens = len(enc.encode(b64))
        analytic = math.ceil(n / 3) * 4 / 4  # ~b64_chars/4
        rows.append({
            "file_bytes": n,
            "b64_chars": len(b64),
            "tokens_o200k": tokens,
            "analytic_tokens": analytic,
            "tokens_per_byte": tokens / n,
        })
    return rows


def _cap_crossover(rows: list[dict]) -> int | None:
    """Smallest file size whose base64 token count exceeds the tool cap."""
    for r in rows:
        if r["tokens_o200k"] > TOOL_TOKEN_CAP:
            return r["file_bytes"]
    return None


def plot(rows: list[dict], out: Path) -> None:
    xs = [r["file_bytes"] for r in rows]
    ys = [r["tokens_o200k"] for r in rows]
    ya = [r["analytic_tokens"] for r in rows]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(xs, ys, "o-", color="#c0392b", label="base64-in-context (tiktoken o200k_base)")
    ax.plot(xs, ya, "--", color="#7f8c8d", label="analytic ≈ b64_chars / 4")
    ax.axhline(TOOL_TOKEN_CAP, color="#2c3e50", ls=":", lw=1.5,
               label=f"~{TOOL_TOKEN_CAP:,}-token tool-output cap")
    ax.axhline(40, color="#27ae60", ls="-", lw=1.5,
               label="new metadata-only path (~40 tokens, constant)")

    cross = _cap_crossover(rows)
    if cross:
        ax.axvline(cross, color="#e67e22", ls="-.", lw=1.2)
        ax.annotate(f"cap breached at ~{cross:,} B",
                    xy=(cross, TOOL_TOKEN_CAP), xytext=(cross, TOOL_TOKEN_CAP * 20),
                    color="#e67e22", ha="center", fontsize=9,
                    arrowprops=dict(arrowstyle="->", color="#e67e22"))

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("file size (bytes, log scale)")
    ax.set_ylabel("tool-result tokens (log scale)")
    ax.set_title("Token cost of base64-in-context downloads vs file size")
    ax.grid(True, which="both", ls=":", alpha=0.4)
    ax.legend(fontsize=8, loc="upper left")
    fig.text(0.5, -0.02,
             "Base64-in-context token cost is ~linear in file size; the new tool returns "
             "constant ~40-token metadata regardless of size.",
             ha="center", fontsize=8, style="italic")
    fig.tight_layout()
    fig.savefig(out, dpi=130, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    rows = measure()
    with open(REPORT_DIR / "token_scaling.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    plot(rows, REPORT_DIR / "token_scaling.png")

    cross = _cap_crossover(rows)
    tpb = sum(r["tokens_per_byte"] for r in rows) / len(rows)
    print(f"tokens/byte (mean): {tpb:.3f}")
    print(f"~10k-token tool cap breached at file size: "
          f"{cross:,} bytes ({cross / 1024:.1f} KiB)" if cross else "cap not reached")
    print(f"wrote {REPORT_DIR / 'token_scaling.csv'} and token_scaling.png")


if __name__ == "__main__":
    main()
