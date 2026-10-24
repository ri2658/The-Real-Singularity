"""Show week-3 results: seed table, loss vs. true error, PINN vs. reference.

Run from the repo root:
    python scripts/show_results.py                       # uses runs/p1000_8x20_s*
    python scripts/show_results.py --runs runs/lbfgs_8x20_s0 runs/lbfgs_8x20_s1
    python scripts/show_results.py --no-show             # only save the PNGs

Outputs (also saved as PNG in results/):
    1. table of final relative L2 per run (printed)
    2. loss_vs_error.png      training loss and true error vs. step, per run
    3. pinn_vs_reference.png  reference, PINN and |error| over (x, t) for the best run,
                              plus u(x) snapshots before/after the shock forms
"""

import argparse
import glob
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib.pyplot as plt
import numpy as np
import torch

from pinn.reference import load_reference, reference_path
from pinn.runlog import load_run, load_checkpoint


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--runs", nargs="*", default=None,
                   help="run folders (default: runs/p1000_8x20_s*)")
    p.add_argument("--out", default="results", help="folder for the PNGs")
    p.add_argument("--no-show", action="store_true", help="save PNGs without opening windows")
    return p.parse_args()


def summarize(run_dirs):
    rows = []
    for d in run_dirs:
        cfg, hist = load_run(d)
        summ = json.load(open(Path(d) / "summary.json"))
        adam_end = [h for h in hist if h["phase"] == "adam"][-1]
        rows.append({
            "dir": d, "cfg": cfg, "hist": hist,
            "seed": cfg["seed"],
            "adam_rel_l2": adam_end["rel_l2"],
            "final_step": summ["final_step"],
            "final_loss": summ["final_loss_total"],
            "final_rel_l2": summ["final_rel_l2"],
            "minutes": summ["wall_time_s"] / 60,
        })

    print(f"\n{'run':<24}{'seed':>5}{'after Adam':>13}{'final rel L2':>14}{'final loss':>12}{'steps':>7}{'min':>6}")
    for r in rows:
        print(f"{Path(r['dir']).name:<24}{r['seed']:>5}{r['adam_rel_l2']:>13.2e}"
              f"{r['final_rel_l2']:>14.2e}{r['final_loss']:>12.2e}{r['final_step']:>7}{r['minutes']:>6.0f}")
    errs = np.array([r["final_rel_l2"] for r in rows])
    print(f"\nfinal rel L2 over {len(errs)} runs: median {np.median(errs):.2e}, "
          f"range {errs.min():.2e} - {errs.max():.2e}, below 1e-3: {(errs < 1e-3).sum()}/{len(errs)}\n")
    return rows


def plot_loss_vs_error(rows, out):
    n = len(rows)
    cols = min(n, 3)
    nrows = math.ceil(n / cols)
    fig, axes = plt.subplots(nrows, cols, figsize=(5.2 * cols, 3.8 * nrows), squeeze=False)
    for ax, r in zip(axes.flat, rows):
        h = r["hist"]
        steps = [e["step"] for e in h]
        ax.plot(steps, [e["loss_total"] for e in h], color="tab:blue", label="training loss")
        ax.plot(steps, [e["rel_l2"] for e in h], color="tab:red", label="true error (rel L2)")
        switch = [e["step"] for e in h if e["phase"] == "adam"][-1]
        ax.axvline(switch, color="gray", ls="--", lw=1)
        ax.text(switch, 1.2, " L-BFGS", color="gray", va="top", fontsize=8)
        ax.axhline(1e-3, color="green", ls=":", lw=1)
        ax.set_yscale("log")
        ax.set_title(f"seed {r['seed']}: final rel L2 = {r['final_rel_l2']:.1e}", fontsize=10)
        ax.set_xlabel("step")
    for ax in list(axes.flat)[n:]:
        ax.axis("off")
    axes.flat[0].legend(fontsize=8, loc="lower left")
    fig.suptitle("Training loss vs. true error (dotted line: 1e-3 target)")
    fig.tight_layout()
    path = Path(out) / "loss_vs_error.png"
    fig.savefig(path, dpi=150)
    print(f"saved {path}")


def plot_pinn_vs_reference(best, out):
    cfg = best["cfg"]
    nu_pi = round(cfg["nu"] * math.pi, 6)
    ref = load_reference(reference_path(nu_pi))
    model = load_checkpoint(best["dir"])

    X, T = np.meshgrid(ref["x"], ref["t"], indexing="ij")
    with torch.no_grad():
        U_pinn = model(torch.tensor(X.reshape(-1, 1), dtype=torch.float32),
                       torch.tensor(T.reshape(-1, 1), dtype=torch.float32)).numpy().reshape(X.shape)
    U_ref = ref["U"]
    err = np.abs(U_pinn - U_ref)

    fig = plt.figure(figsize=(15, 7.5))
    extent = [ref["t"][0], ref["t"][-1], ref["x"][0], ref["x"][-1]]
    panels = [(U_ref, "reference u(x, t)", "RdBu_r", (-1, 1)),
              (U_pinn, "PINN u(x, t)", "RdBu_r", (-1, 1)),
              (err, "|PINN - reference|", "magma", (0, err.max()))]
    for i, (Z, title, cmap, (vmin, vmax)) in enumerate(panels):
        ax = fig.add_subplot(2, 3, i + 1)
        im = ax.imshow(Z, origin="lower", aspect="auto", extent=extent, cmap=cmap, vmin=vmin, vmax=vmax)
        ax.axvline(1 / math.pi, color="k", ls=":", lw=0.8)
        ax.set_title(title)
        ax.set_xlabel("t")
        ax.set_ylabel("x")
        fig.colorbar(im, ax=ax)

    for i, t_val in enumerate((0.25, 0.5, 0.75)):
        j = int(np.argmin(np.abs(ref["t"] - t_val)))
        ax = fig.add_subplot(2, 3, 4 + i)
        ax.plot(ref["x"], U_ref[:, j], "k-", lw=2, label="reference")
        ax.plot(ref["x"], U_pinn[:, j], "r--", lw=1.5, label="PINN")
        when = "before" if ref["t"][j] < 1 / math.pi else "after"
        ax.set_title(f"t = {ref['t'][j]:.2f} ({when} shock forms at t* = 1/pi)", fontsize=10)
        ax.set_xlabel("x")
        if i == 0:
            ax.set_ylabel("u")
            ax.legend(fontsize=8)

    fig.suptitle(f"{Path(best['dir']).name}: nu = {nu_pi}/pi, full-grid rel L2 = {best['final_rel_l2']:.1e}, "
                 f"max |error| = {err.max():.1e}")
    fig.tight_layout()
    path = Path(out) / "pinn_vs_reference.png"
    fig.savefig(path, dpi=150)
    print(f"saved {path}")


def main():
    a = parse_args()
    run_dirs = a.runs or sorted(glob.glob("runs/p1000_8x20_s*"))
    if not run_dirs:
        sys.exit("no run folders found; run from the repo root or pass --runs")
    Path(a.out).mkdir(parents=True, exist_ok=True)

    rows = summarize(run_dirs)
    plot_loss_vs_error(rows, a.out)
    plot_pinn_vs_reference(min(rows, key=lambda r: r["final_rel_l2"]), a.out)
    if not a.no_show:
        plt.show()


if __name__ == "__main__":
    main()
