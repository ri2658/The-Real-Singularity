"""Export PINN predictions for the viscosity-slider page (week 6, Beat 1).

For each viscosity nu in {0.01, 0.003, 0.001}/pi and each collocation sampling
(uniform, shock-focused), load one trained run, evaluate u(x, t) on the same
256 x 100 grid as the reference solutions, and write one JSON file per run:

    data/viscosity/pinn_{sampling}_nu{nu_pi}pi.json   {"run", "nu_pi", "sampling", "rel_l2",
                                                       "x", "t", "u"}   u[j][i] = u(x[i], t[j])
    data/viscosity/index.json                          which run was used for each case

u is stored as [t][x], the same layout as data/reference_json/ref_nu*pi.json.

Which run: the median seed by final relative L2 (the typical result, not the best),
except uniform nu = 0.01/pi, which uses p1000_8x20_s1, the model behind the live ONNX
page (site/pinn/), so the site shows one consistent baseline.

Checks (the script stops if one fails):
  1. Each chosen run is what the table below says it is (nu, sampling, depth x width).
  2. rel L2 recomputed here on the .npz reference matches the run's summary.json.
  3. rel L2 of the rounded, exported values against the JSON reference the page uses.

Run from the repo root (needs torch):
    python3 scripts/export_viscosity.py
Then rebuild the site: python3 scripts/build_site.py
"""

import json
import math
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pinn import load_reference, reference_path, rel_l2_grid  # noqa: E402
from pinn.runlog import load_checkpoint  # noqa: E402

OUT = ROOT / "data" / "viscosity"
DECIMALS = 4                      # 1e-4 rounding; the best model's error is ~5e-4 relative

# (sampling, nu_pi) -> candidate runs. Median seed is picked from these,
# unless "fixed" names the run to use.
CASES = {
    ("uniform", 0.01):  {"fixed": "p1000_8x20_s1",
                         "seeds": [f"p1000_8x20_s{i}" for i in range(5)]},
    ("uniform", 0.003): {"seeds": [f"nu0.003_vanilla_s{i}" for i in range(3)]},
    ("uniform", 0.001): {"seeds": [f"nu0.001_vanilla_s{i}" for i in range(3)]},
    ("shock", 0.01):    {"seeds": [f"nu0.01_shock_s{i}" for i in range(3)]},
    ("shock", 0.003):   {"seeds": [f"nu0.003_shock_s{i}" for i in range(3)]},
    ("shock", 0.001):   {"seeds": [f"nu0.001_shock_s{i}" for i in range(3)]},
}


def run_info(name):
    d = ROOT / "runs" / name
    cfg = json.loads((d / "config.json").read_text())
    summ = json.loads((d / "summary.json").read_text())
    return cfg, summ


def median_run(names):
    errs = sorted((run_info(n)[1]["final_rel_l2"], n) for n in names)
    return errs[len(errs) // 2][1], errs


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    index = {"decimals": DECIMALS, "cases": []}
    print(f"{'sampling':8s} {'nu':>7s}  {'run':22s} {'seeds (rel L2)':40s} {'summary':>9s} {'recomp.':>9s} {'exported':>9s}")

    for (sampling, nu_pi), spec in CASES.items():
        med, errs = median_run(spec["seeds"])
        name = spec.get("fixed", med)
        cfg, summ = run_info(name)

        # Check 1: the run is the case we think it is.
        assert abs(cfg["nu"] * math.pi - nu_pi) < 1e-9, (name, cfg["nu"])
        assert cfg.get("sampling", "uniform") == sampling, (name, cfg.get("sampling"))
        assert (cfg["depth"], cfg["width"]) == (8, 20), name

        model = load_checkpoint(ROOT / "runs" / name)

        # Check 2: same error as when it was trained.
        ref_npz = load_reference(reference_path(nu_pi))
        err = rel_l2_grid(model, ref_npz)
        if abs(err - summ["final_rel_l2"]) > 1e-4 * summ["final_rel_l2"] + 1e-7:
            raise SystemExit(f"{name}: recomputed rel L2 {err:.6e} != summary {summ['final_rel_l2']:.6e}")

        # Evaluate on the JSON reference grid (same x, t as the .npz) and round.
        ref = json.loads((ROOT / "data" / "reference_json" / f"ref_nu{nu_pi:g}pi.json").read_text())
        x = np.array(ref["x"]); t = np.array(ref["t"]); U_ref = np.array(ref["u"])     # (nt, nx)
        T, X = np.meshgrid(t, x, indexing="ij")                                          # (nt, nx)
        with torch.no_grad():
            u = model(torch.tensor(X.reshape(-1, 1), dtype=torch.float32),
                      torch.tensor(T.reshape(-1, 1), dtype=torch.float32)).numpy().reshape(X.shape)
        u = np.round(u, DECIMALS)

        # Check 3: what the page will show.
        err_page = float(np.linalg.norm(u - U_ref) / np.linalg.norm(U_ref))

        fname = f"pinn_{sampling}_nu{nu_pi:g}pi.json"
        (OUT / fname).write_text(json.dumps({
            "run": name, "nu_pi": nu_pi, "sampling": sampling, "rel_l2": round(err_page, 6),
            "x": [round(v, 8) for v in x.tolist()], "t": [round(v, 6) for v in t.tolist()],
            "u": [[float(v) for v in row] for row in u.tolist()],
        }, separators=(",", ":")))
        index["cases"].append({"sampling": sampling, "nu_pi": nu_pi, "run": name, "file": fname,
                               "rel_l2": round(err_page, 6),
                               "seeds": [{"run": n, "rel_l2": e} for e, n in errs],
                               "choice": "fixed (same model as the live ONNX page)" if "fixed" in spec else "median seed"})
        seeds = ", ".join(f"{e:.1e}" for e, _ in errs)
        print(f"{sampling:8s} {nu_pi:7g}  {name:22s} {seeds:40s} {summ['final_rel_l2']:9.2e} {err:9.2e} {err_page:9.2e}")

    (OUT / "index.json").write_text(json.dumps(index, indent=1))
    size = sum(p.stat().st_size for p in OUT.glob("*.json")) / 1e6
    print(f"\nwrote {len(index['cases'])} runs + index.json to {OUT.relative_to(ROOT)}/ ({size:.2f} MB)")


if __name__ == "__main__":
    main()
