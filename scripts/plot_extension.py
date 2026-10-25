"""Plot what extra L-BFGS steps do after early stopping.

Each pair is (original run, extended run). The extended run is the same seed and
setup retrained with early stopping off, so its history matches the original up to
the original stop step and then continues. The script checks that match.

Output: results/extension_<names>.png with, per seed, training loss (top) and true
error (bottom) on a shared step axis; the shaded band is the extra steps.

Run from the repo root:
    python scripts/plot_extension.py runs/p1000_8x20_s0 runs/p1000_8x20_s0_ext2k \
                                     runs/p1000_8x20_s2 runs/p1000_8x20_s2_ext2k
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib.pyplot as plt
import numpy as np

from pinn.runlog import load_run

INK, INK_MUTED, GRID = "#0b0b0b", "#6b6a64", "#e4e3de"
LOSS_COLOR, ERR_COLOR = "#2a78d6", "#eb6834"


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("runs", nargs="+", help="pairs: original_run extended_run ...")
    p.add_argument("--out", default="results")
    p.add_argument("--no-show", action="store_true")
    a = p.parse_args()
    if len(a.runs) % 2:
        p.error("give runs in pairs: original extended")
    return a


def style(ax):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(INK_MUTED)
    ax.tick_params(colors=INK_MUTED, labelcolor=INK)
    ax.grid(True, color=GRID, lw=0.8)
    ax.set_axisbelow(True)


def check_match(orig_hist, ext_hist):
    """Max relative difference of loss and rel_l2 over the steps both runs logged."""
    ext_by_step = {e["step"]: e for e in ext_hist}
    worst = 0.0
    for e in orig_hist:
        f = ext_by_step.get(e["step"])
        if f is None:
            continue
        for k in ("loss_total", "rel_l2"):
            worst = max(worst, abs(e[k] - f[k]) / max(abs(e[k]), 1e-30))
    return worst


def main():
    a = parse_args()
    pairs = [(Path(a.runs[i]), Path(a.runs[i + 1])) for i in range(0, len(a.runs), 2)]
    fig, axes = plt.subplots(2, len(pairs), figsize=(6.2 * len(pairs), 6.4),
                             sharex="col", squeeze=False)

    for j, (orig_dir, ext_dir) in enumerate(pairs):
        cfg, orig = load_run(orig_dir)
        _, ext = load_run(ext_dir)
        stop = orig[-1]["step"]
        mismatch = check_match(orig, ext)
        at_stop = min(ext, key=lambda e: abs(e["step"] - stop))
        end = ext[-1]
        print(f"{orig_dir.name}: stopped at {stop}; extended to {end['step']}; "
              f"max rel. difference before stop = {mismatch:.1e}")
        print(f"   loss   {at_stop['loss_total']:.3e} -> {end['loss_total']:.3e} "
              f"({at_stop['loss_total'] / end['loss_total']:.2f}x lower)")
        print(f"   rel_l2 {at_stop['rel_l2']:.3e} -> {end['rel_l2']:.3e} "
              f"({at_stop['rel_l2'] / end['rel_l2']:.2f}x lower)")

        steps = np.array([e["step"] for e in ext])
        for i, (key, color, label) in enumerate((("loss_total", LOSS_COLOR, "training loss"),
                                                  ("rel_l2", ERR_COLOR, "true error (rel L²)"))):
            ax = axes[i, j]
            style(ax)
            ax.axvspan(stop, steps[-1], color=GRID, alpha=0.6, lw=0)
            ax.axvline(stop, color=INK_MUTED, ls="--", lw=1)
            ax.plot(steps, [e[key] for e in ext], color=color, lw=2)
            ax.set_yscale("log")
            ax.set_ylabel(label, color=INK)
            v0, v1 = at_stop[key], end[key]
            ax.annotate(f"{v0:.2e}", (stop, v0), xytext=(-6, 8), textcoords="offset points",
                        ha="right", fontsize=8, color=INK)
            ax.annotate(f"{v1:.2e}", (steps[-1], v1), xytext=(-2, 8), textcoords="offset points",
                        ha="right", fontsize=8, color=INK)
            if i == 0:
                ax.set_title(f"seed {cfg['seed']}: stopped at step {stop}, +{steps[-1] - stop} steps",
                             fontsize=10, color=INK)
                ax.text(stop, ax.get_ylim()[1], " extra steps", va="top", fontsize=8, color=INK_MUTED)
            else:
                ax.set_xlabel("training step", color=INK)
                ax.axhline(1e-3, color=INK_MUTED, ls=":", lw=1)

    fig.suptitle("Continuing L-BFGS after early stopping (ν = 0.01/π)", color=INK)
    fig.tight_layout()
    Path(a.out).mkdir(parents=True, exist_ok=True)
    name = "_".join(p[0].name for p in pairs)
    path = Path(a.out) / f"extension_{name}.png"
    fig.savefig(path, dpi=150)
    print(f"saved {path}")
    if not a.no_show:
        plt.show()


if __name__ == "__main__":
    main()
