"""
Step 2: compare the finite-volume solver with the three reference files.

Put this file in the same folder as burgers_fv.py (e.g. "Finite volume solver/").
It finds data/reference/ relative to this file, so it works from any directory.

Reference file layout (from CheckReference.py):
    x  (256,)      grid points
    t  (100,)      times
    U  (256, 100)  rows = x, columns = t
    nu ()          viscosity stored inside the file (no need to guess it)
"""

import csv
import time
from pathlib import Path

import numpy as np

from Burgersfv import rel_l2, solve

REF_DIR = Path(__file__).resolve().parent.parent / "data" / "reference"
N_LIST = (500, 1000, 2000, 4000)          # numbers of cells to try


def solve_on_reference_grid(nu, N, x_ref, t_ref):
    """Run the solver and return u on the reference grid, shape (nx, nt)."""
    x_c, snaps = solve(nu, N, t_ref)                  # snaps: (nt, N) at cell centres
    # The solver stores cell-centre values. The reference lives on its own x grid,
    # so we interpolate linearly. We add the two wall points (u = 0 at x = +-1)
    # so that np.interp does not extrapolate with a wrong constant near the walls.
    xs = np.concatenate(([-1.0], x_c, [1.0]))
    cols = []
    for s in snaps:
        us = np.concatenate(([0.0], s, [0.0]))
        cols.append(np.interp(x_ref, xs, us))
    return np.array(cols).T                           # (nx, nt), same layout as U


def main():
    files = sorted(REF_DIR.glob("burgers_nu*.npz"))
    if not files:
        raise SystemExit(f"No reference files found in {REF_DIR}")

    rows = []
    for path in files:
        ref = np.load(path)
        x_ref, t_ref, U_ref, nu = ref["x"], ref["t"], ref["U"], float(ref["nu"])
        print(f"\n{path.name}: nu = {nu:.6e} = {nu * np.pi:.4g}/pi, "
              f"x in [{x_ref[0]:.3g}, {x_ref[-1]:.3g}], t in [{t_ref[0]:.3g}, {t_ref[-1]:.3g}]")

        for N in N_LIST:
            t0 = time.perf_counter()
            U_sol = solve_on_reference_grid(nu, N, x_ref, t_ref)
            sec = time.perf_counter() - t0
            err = rel_l2(U_sol, U_ref)                         # whole (x, t) grid at once
            err_t1 = rel_l2(U_sol[:, -1], U_ref[:, -1])        # last time only
            print(f"   N = {N:5d}   rel L2 = {err:.3e}   (t = {t_ref[-1]:.2g} only: {err_t1:.3e})   "
                  f"python time {sec:5.2f} s")
            rows.append((path.name, nu * np.pi, N, err, err_t1, sec))

    out = Path(__file__).resolve().parent / "fv_vs_reference.csv"
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file", "nu_times_pi", "N", "rel_l2_all", "rel_l2_last_t", "python_seconds"])
        w.writerows(rows)
    print(f"\nsaved {out}")


if __name__ == "__main__":
    main()