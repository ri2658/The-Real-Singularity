"""Summarize the week-4 nu sweep: uniform vs. shock-focused collocation.

Finds every run in runs/ whose config matches the sweep setup (8 x 20 xavier,
10k collocation points, Adam 2000 + L-BFGS, patience 1000, seeds 0-2), groups
them by (nu, sampling) and writes:

    results/sweep_table.csv          one row per (nu, sampling): median / min / max rel L2
    results/sweep_error_vs_nu.png    median rel L2 vs nu, whisker = min-max over seeds
    results/sweep_snapshots.png      u(x) near the shock at t = 0.75, median-seed run
                                     of each (nu, sampling), against the reference

Run from the repo root:
    python scripts/summarize_sweep.py
    python scripts/summarize_sweep.py --no-show
"""

import argparse
import csv
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib.pyplot as plt
import numpy as np
import torch

from pinn.reference import load_reference, reference_path
from pinn.runlog import load_checkpoint

SWEEP_SETUP = {"depth": 8, "width": 20, "init": "xavier", "n_col": 10000,
               "adam_steps": 2000, "lbfgs_patience": 1000}
METHODS = ("uniform", "shock")
COLORS = {"uniform": "#2a78d6", "shock": "#eb6834"}   # validated categorical slots 1-2
LABELS = {"uniform": "uniform collocation", "shock": "shock-focused collocation"}
INK, INK_MUTED, GRID = "#0b0b0b", "#6b6a64", "#e4e3de"


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--runs-dir", default="runs")
    p.add_argument("--seeds", type=int, nargs="*", default=[0, 1, 2])
    p.add_argument("--out", default="results")
    p.add_argument("--no-show", action="store_true")
    return p.parse_args()


def collect(runs_dir, seeds):
    groups = {}
    for cfg_path in sorted(Path(runs_dir).glob("*/config.json")):
        run = cfg_path.parent
        summ_path = run / "summary.json"
        if not summ_path.exists():
            continue
        cfg = json.load(open(cfg_path))
        if any(cfg.get(k) != v for k, v in SWEEP_SETUP.items()) or cfg.get("seed") not in seeds:
            continue
        nu_pi = round(cfg["nu"] * math.pi, 6)
        method = cfg.get("sampling", "uniform")   # week-3 runs predate the field
        summ = json.load(open(summ_path))
        groups.setdefault((nu_pi, method), []).append(
            {"dir": run, "seed": cfg["seed"], "rel_l2": summ["final_rel_l2"]})
    return groups


def write_table(groups, out):
    rows = []
    print(f"\n{'nu':>9} {'sampling':<9} {'n':>2} {'median':>10} {'min':>10} {'max':>10}   runs")
    for (nu_pi, method) in sorted(groups, key=lambda k: (-k[0], METHODS.index(k[1]))):
        g = sorted(groups[(nu_pi, method)], key=lambda r: r["seed"])
        e = np.array([r["rel_l2"] for r in g])
        row = {"nu": f"{nu_pi:g}/pi", "sampling": method, "n_seeds": len(e),
               "median_rel_l2": np.median(e), "min_rel_l2": e.min(), "max_rel_l2": e.max(),
               "runs": " ".join(r["dir"].name for r in g)}
        rows.append(row)
        print(f"{row['nu']:>9} {method:<9} {len(e):>2} {row['median_rel_l2']:>10.2e} "
              f"{row['min_rel_l2']:>10.2e} {row['max_rel_l2']:>10.2e}   {row['runs']}")
    path = Path(out) / "sweep_table.csv"
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"\nsaved {path}")


def style(ax):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(INK_MUTED)
    ax.tick_params(colors=INK_MUTED, labelcolor=INK)
    ax.grid(True, which="major", color=GRID, lw=0.8)
    ax.set_axisbelow(True)


def plot_error_vs_nu(groups, out):
    nus = sorted({k[0] for k in groups}, reverse=True)
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    style(ax)
    for i, method in enumerate(METHODS):
        xs, med, lo, hi = [], [], [], []
        for j, nu_pi in enumerate(nus):
            g = groups.get((nu_pi, method))
            if not g:
                continue
            e = np.array([r["rel_l2"] for r in g])
            xs.append(j + (i - 0.5) * 0.12)
            med.append(np.median(e)); lo.append(e.min()); hi.append(e.max())
        med, lo, hi = map(np.array, (med, lo, hi))
        ax.errorbar(xs, med, yerr=[med - lo, hi - med], fmt="o-", color=COLORS[method],
                    lw=2, ms=8, capsize=4, elinewidth=1.5, label=LABELS[method],
                    markeredgecolor="white", markeredgewidth=1.5)
    ax.axhline(1e-3, color=INK_MUTED, ls=":", lw=1)
    ax.text(len(nus) - 0.55, 1.15e-3, "week-3 target 1e-3", color=INK_MUTED, fontsize=8,
            va="bottom", ha="right")
    ax.set_yscale("log")
    ax.set_xticks(range(len(nus)), [f"{n:g}/π" for n in nus])
    ax.set_xlim(-0.4, len(nus) - 0.6)
    ax.set_xlabel("viscosity ν (smaller = steeper shock)", color=INK)
    ax.set_ylabel("relative L² error (full grid)", color=INK)
    ax.set_title("PINN error vs. viscosity: median of 3 seeds, bars = min–max", color=INK, fontsize=11)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    fig.tight_layout()
    path = Path(out) / "sweep_error_vs_nu.png"
    fig.savefig(path, dpi=150)
    print(f"saved {path}")


def plot_snapshots(groups, out, t_val=0.75, half_width=0.3):
    nus = sorted({k[0] for k in groups}, reverse=True)
    fig, axes = plt.subplots(len(METHODS), len(nus), figsize=(4.2 * len(nus), 6.4),
                             sharex=True, sharey=True, squeeze=False)
    for j, nu_pi in enumerate(nus):
        ref = load_reference(reference_path(nu_pi))
        k = int(np.argmin(np.abs(ref["t"] - t_val)))
        mask = np.abs(ref["x"]) <= half_width
        x_fine = np.linspace(-half_width, half_width, 601)
        for i, method in enumerate(METHODS):
            ax = axes[i, j]
            style(ax)
            g = groups.get((nu_pi, method))
            if not g:
                ax.axis("off")
                continue
            g = sorted(g, key=lambda r: r["rel_l2"])
            run = g[len(g) // 2]                       # median-error seed
            model = load_checkpoint(run["dir"])
            with torch.no_grad():
                u = model(torch.tensor(x_fine[:, None], dtype=torch.float32),
                          torch.full((len(x_fine), 1), float(ref["t"][k]))).numpy().ravel()
            ax.plot(ref["x"][mask], ref["U"][mask, k], color=INK, lw=2, label="reference")
            ax.plot(x_fine, u, color=COLORS[method], lw=2, ls="--", label="PINN")
            ax.set_title(f"ν = {nu_pi:g}/π, {method}: rel L² {run['rel_l2']:.1e}",
                         fontsize=10, color=INK)
            if i == len(METHODS) - 1:
                ax.set_xlabel("x", color=INK)
            if j == 0:
                ax.set_ylabel("u", color=INK)
                ax.legend(frameon=False, fontsize=8, loc="lower left")
    fig.suptitle(f"Near the shock at t = {t_val} (median-seed run of each setting)", color=INK)
    fig.tight_layout()
    path = Path(out) / "sweep_snapshots.png"
    fig.savefig(path, dpi=150)
    print(f"saved {path}")


def main():
    a = parse_args()
    groups = collect(a.runs_dir, set(a.seeds))
    if not groups:
        sys.exit("no matching runs found; run from the repo root")
    Path(a.out).mkdir(parents=True, exist_ok=True)
    write_table(groups, a.out)
    plot_error_vs_nu(groups, a.out)
    plot_snapshots(groups, a.out)
    if not a.no_show:
        plt.show()


if __name__ == "__main__":
    main()
