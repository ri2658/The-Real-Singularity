"""
Step 3: export data for the browser (JavaScript cannot read .npz files).

Writes into  <repo>/data/reference_json/  :
    ref_<name>.json       reference solution: nu, x, t, u[ti][xi]   (time-major)
    pycheck_<name>.json   Python solver output (N = 1000) at t = 0.25, 0.5, 0.75, 1.0
                          -> used in Step 4 to check that the JS port gives the same numbers

Put this file next to burgers_fv.py ("Finite volume solver/").
"""

import json
from pathlib import Path

import numpy as np

from Burgersfv import solve

ROOT = Path(__file__).resolve().parent.parent
REF_DIR = ROOT / "data" / "reference"
OUT_DIR = ROOT / "data" / "reference_json"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CHECK_TIMES = [0.25, 0.5, 0.75, 1.0]
CHECK_N = 1000

for path in sorted(REF_DIR.glob("burgers_nu*.npz")):
    ref = np.load(path)
    x, t, U, nu = ref["x"], ref["t"], ref["U"], float(ref["nu"])
    name = path.stem.replace("burgers_", "")                   # e.g. nu0.01pi

    # Reference: transpose to time-major, so JS reads u[ti][xi] = profile at time ti.
    # 6 decimals is far below any error we report (1e-3) and keeps the file small.
    ref_json = {"nu": nu, "x": np.round(x, 8).tolist(), "t": np.round(t, 8).tolist(),
                "u": np.round(U.T, 6).tolist()}
    (OUT_DIR / f"ref_{name}.json").write_text(json.dumps(ref_json, separators=(",", ":")))

    # Python solver output for the JS-vs-Python check (full precision on purpose).
    xc, snaps = solve(nu, CHECK_N, CHECK_TIMES)
    py_json = {"nu": nu, "N": CHECK_N, "times": CHECK_TIMES, "x": xc.tolist(), "u": snaps.tolist()}
    (OUT_DIR / f"pycheck_{name}.json").write_text(json.dumps(py_json, separators=(",", ":")))

    size_kb = (OUT_DIR / f"ref_{name}.json").stat().st_size / 1024
    print(f"{name}: nu = {nu:.4e}, u shape (t, x) = {U.T.shape}, ref json {size_kb:.0f} KB")

print(f"\nwritten to {OUT_DIR}")