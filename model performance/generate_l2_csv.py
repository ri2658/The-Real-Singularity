import csv
import glob
import os
import re

import numpy as np
import torch


# ---- reference solution and L2 (copied from the notebook) -------------------

def burgers_exact(x, t, nu, n=200):
    """Cole-Hopf solution for u(x,0) = -sin(pi x). x: 1D array, t: scalar > 0."""
    z, w = np.polynomial.hermite.hermgauss(n)
    x = np.asarray(x)[:, None]
    y = x - 2 * np.sqrt(nu * t) * z[None, :]
    logf = -np.cos(np.pi * y) / (2 * np.pi * nu)
    logf -= logf.max(axis=1, keepdims=True)          # avoids overflow for small nu
    f = np.exp(logf)
    return (-np.sin(np.pi * y) * f * w).sum(axis=1) / (f * w).sum(axis=1)


def build_table(nu, nx=256, nt=100):
    """(x, t, u) reference table on a grid; t starts at 0.01 because the formula needs t > 0."""
    xs = np.linspace(-1, 1, nx)
    ts = np.linspace(0.01, 1, nt)
    U = np.stack([burgers_exact(xs, t, nu) for t in ts], axis=1)   # (nx, nt)
    X, T = np.meshgrid(xs, ts, indexing="ij")
    return np.column_stack([X.ravel(), T.ravel(), U.ravel()])


def rel_l2_grid(model, table):
    x = torch.tensor(table[:, 0:1], dtype=torch.float32)
    t = torch.tensor(table[:, 1:2], dtype=torch.float32)
    with torch.no_grad():
        u = model(x, t).numpy().ravel()
    return np.linalg.norm(u - table[:, 2]) / np.linalg.norm(table[:, 2])


# ---- CSV generation ---------------------------------------------------------

def generate_l2_csv(ckpt_dir, model_class, nu=0.01 / np.pi,
                    out_csv="l2_history.csv", pattern="*.pt"):
    """
    For every .pt file in ckpt_dir, load the weights, compute the relative L2
    error on the whole (x, t) grid, and write a CSV with columns: iteration, l2.
    The iteration is the LAST number in the file name (adam_5000.pt -> 5000).
    """
    table = build_table(nu)                            # built once, reused for every file

    rows = []
    for path in glob.glob(os.path.join(ckpt_dir, pattern)):
        nums = re.findall(r"\d+", os.path.basename(path))
        if not nums:
            print(f"skipped (no iteration number in name): {path}")
            continue

        state = torch.load(path, weights_only=True)
        if "model" in state and isinstance(state["model"], dict):   # full checkpoint dict
            state = state["model"]

        model = model_class()
        model.load_state_dict(state)
        model.eval()
        rows.append((int(nums[-1]), float(rel_l2_grid(model, table))))

    rows.sort(key=lambda r: r[0])
    with open(out_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["iteration", "l2"])
        w.writerows(rows)
    print(f"wrote {len(rows)} rows to {out_csv}")
    return rows


if __name__ == "__main__":
    from model import SimplePINN        # the .py file that holds the SimplePINN class

    generate_l2_csv("runs/nu0.01pi_seed0/ckpt", SimplePINN,
                    nu=0.01 / np.pi, out_csv="l2_history.csv")
