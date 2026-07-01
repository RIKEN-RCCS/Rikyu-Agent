"""Plot the transport wall-clock landscape from benchmark.csv.

Reads the sweep produced by bench_download.py and renders mean wall-clock per
transport vs file size on log-log axes, with asymmetric error bars spanning the
min..max of the 10 repetitions (the full spread — this is a landscape, not a
hypothesis test). rm_rsync's 100 MB failure is marked.

    cd server && uv run python tests/plot_benchmark.py

Writes __reports__/fs-download-rework/wallclock.png.
"""
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPORT_DIR = Path(__file__).resolve().parents[2] / "__reports__" / "fs-download-rework"

_COLORS = {"base64": "#c0392b", "rsync": "#2980b9", "scp": "#27ae60", "rm_rsync": "#8e44ad"}


def load(csv_path: Path) -> dict:
    """Return {transport: {"x":[bytes], "mean":[s], "lo":[s], "hi":[s], "fail":[bytes]}}."""
    series: dict[str, dict] = {}
    with open(csv_path) as f:
        for row in csv.DictReader(f):
            if not row.get("transport") or row.get("mean_s") is None:
                continue
            t = row["transport"]
            s = series.setdefault(t, {"x": [], "mean": [], "lo": [], "hi": [], "fail": []})
            size = int(row["size_bytes"])
            if row.get("skipped") == "True" or not row["mean_s"]:
                s["fail"].append(size)
                continue
            mean = float(row["mean_s"])
            s["x"].append(size)
            s["mean"].append(mean)
            s["lo"].append(mean - float(row["min_s"]))   # lower error extent
            s["hi"].append(float(row["max_s"]) - mean)   # upper error extent
    return series


def plot_wallclock(series: dict, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    for t, s in sorted(series.items()):
        if not s["x"]:
            continue
        ax.errorbar(s["x"], s["mean"], yerr=[s["lo"], s["hi"]],
                    fmt="o-", capsize=4, lw=1.6, color=_COLORS.get(t, None), label=t)
        # mark failures at a sensible y (top of that transport's range)
        for fx in s["fail"]:
            ymax = max(s["mean"]) if s["mean"] else 1.0
            ax.scatter([fx], [ymax], marker="x", s=80, color=_COLORS.get(t, "black"), zorder=5)
            ax.annotate(f"{t} failed", xy=(fx, ymax), xytext=(fx, ymax * 1.4),
                        color=_COLORS.get(t, "black"), fontsize=8, ha="center")

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("file size (bytes, log scale)")
    ax.set_ylabel("wall-clock seconds (log scale)")
    ax.set_title("Download transport wall-clock vs file size (mean ± min–max over 10 reps)")
    ax.grid(True, which="both", ls=":", alpha=0.4)
    ax.legend(title="transport", fontsize=9)
    fig.text(0.5, -0.02,
             "Error bars span the min–max of 10 repetitions. base64 wins for tiny files; "
             "rsync/scp win at scale; rm_rsync failed at 100 MB.",
             ha="center", fontsize=8, style="italic")
    fig.tight_layout()
    fig.savefig(out, dpi=130, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    series = load(REPORT_DIR / "benchmark.csv")
    out = REPORT_DIR / "wallclock.png"
    plot_wallclock(series, out)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
