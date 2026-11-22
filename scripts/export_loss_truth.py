"""Export training histories for the loss-vs-truth page.

Collects
    week 3   p1000_8x20_s0..s4                          nu = 0.01/pi, fixed uniform points
    week 4   nu{0.01,0.003,0.001}_{vanilla,shock}_s*     fixed uniform / fixed shock-packed points
    week 5   nu{0.003,0.001}_{rad,resample}_s*_{gpu,cpu}  points redrawn during training
             nu0.003_adamonly_s*_{gpu,cpu}                fixed uniform points, Adam only (control)
             (the suffix is the device it trained on; unfinished runs, without final.pt, are skipped)
and writes, for each run:

    name, nu_pi, sampling, seed, adam_steps, lbfgs (false for the Adam-only control)
    step, loss, loss_pde, err     the logged history (every 50 steps): total training
                                  loss, its PDE term, and the relative L2 error
    fresh: {step, loss, pde}      the same score, re-graded on NEW points (every 500 steps)
    jump_x                        where the PINN puts the jump at t = 1

"New points" score (pinn/fresh.py): the PDE residual on one fixed set of 200,000 points,
x ~ U[-1, 1], t ~ U[0, 1], drawn once from torch.Generator().manual_seed(12345) as a
single (N, 2) draw, the same set for every run and every checkpoint.

    fresh.pde  = mean r^2 on the new points
    fresh.loss = w_pde * fresh.pde + w_ic * loss_ic + w_bc * loss_bc

with the weights from config.json and loss_ic / loss_bc from the history entry at the
same step: only the collocation term changes, the IC / BC points are the same. Week-5
runs log fresh.pde during training (history key loss_pde_fresh); for those the logged
value is used and checked against a recomputation from the checkpoint. Older runs are
recomputed from their checkpoints.

jump_x: u(x, 1) from the final weights on a fine x grid; the jump is where u falls
fastest (most negative du/dx). For u(x, 0) = -sin(pi x) the exact jump stays at x = 0.

Sanity checks (the script stops if one fails):
    - rel_l2 recomputed from final.pt matches the logged value to 3 significant figures
    - new / own PDE ratio stays near 1 (within 3x; mostly 1.0-1.2, a little higher on an
      Adam spike) at every checkpoint up to step 2000 of the runs with evenly spread points
      (fixed or redrawn). After the switch to L-BFGS it reaches thousands in the trap runs.
      Runs that pack their points where the residual is large (shock, rad) are only printed:
      their own score is graded where the equation is hardest, so the ratio is below 1.
    - the medium-fluid runs with extra points at the jump end with a ratio of 0.6 to 1
    - nu0.003_vanilla_s2 ends with a new-point PDE term between 3 and 12 (about 6;
      the residual spikes are narrow, so the exact value depends on the point set)
    - a logged new-point PDE term matches its recomputation within 2%
Stability check: the new-point PDE term is recomputed at every checkpoint on a second
point set (CHECK_SEED) and the largest difference is printed; it must stay under a
factor of 3 (well inside one order of magnitude).

Output: data/loss_truth/runs.json (copied into site/data/ by build_site.py).
The numbers quoted in the page text are printed by scripts/loss_truth_numbers.py.

Run from the repo root (about 10 minutes on a laptop CPU, 2-3 on the GPU):
    python scripts/export_loss_truth.py
    .venv-gpu/Scripts/python scripts/export_loss_truth.py --device cuda
"""

import argparse
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pinn.fresh import FRESH_N, FRESH_SEED, fresh_points, mean_r2           # noqa: E402
from pinn.reference import load_reference, reference_path, rel_l2_grid       # noqa: E402
from pinn.runlog import list_checkpoints, load_checkpoint, load_run          # noqa: E402

RUN_NAME = re.compile(r"^(p1000_8x20_s\d|nu0\.\d+_(vanilla|shock)_s\d|nu0\.\d+_(rad|resample|adamonly)_s\d_(gpu|cpu))$")
CHECK_SEED = 2026
SWITCH = 2000          # end of the Adam phase in every run that has an L-BFGS phase


def jump_position(model, t=1.0, n=8001):
    """x where u(x, t) falls fastest: the PINN's jump."""
    device = next(model.parameters()).device
    x = torch.linspace(-1.0, 1.0, n, device=device).view(-1, 1)
    with torch.no_grad():
        u = model(x, torch.full_like(x, t)).squeeze(1).cpu().double().numpy()
    i = int(np.argmin(np.diff(u)))
    x = x.squeeze(1).cpu().numpy()
    return float((x[i] + x[i + 1]) / 2)


def sig3(v):
    return float(f"{v:.3g}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="cpu", help="cpu or cuda (needs the CUDA build of torch)")
    device = ap.parse_args().device
    pts = fresh_points(device=device)
    pts_check = fresh_points(seed=CHECK_SEED, device=device)
    failures = []

    def check(ok, msg):
        print(("  ok    " if ok else "  FAIL  ") + msg)
        if not ok:
            failures.append(msg)

    runs = []
    for d in sorted((ROOT / "runs").iterdir()):
        if not RUN_NAME.match(d.name):
            continue
        if not (d / "final.pt").exists():
            print(f"\n{d.name}: no final.pt (unfinished), skipped")
            continue
        cfg, hist = load_run(d)
        nu, w = cfg["nu"], cfg["weights"]
        sampling = cfg.get("sampling", "uniform")
        lbfgs = cfg.get("lbfgs_steps", 0) > 0
        by_step = {e["step"]: e for e in hist}
        final = hist[-1]
        logged = [e["step"] for e in hist if e.get("loss_pde_fresh") is not None]

        if logged:
            steps = logged
        else:
            steps = [s for s in list_checkpoints(d) if s in by_step and s != final["step"]] + [final["step"]]
        fresh = {"step": [], "loss": [], "pde": []}
        ratio_check, log_diff = [], []
        print(f"\n{d.name}  (nu = {nu * math.pi:g}/pi, {sampling}, seed {cfg['seed']}"
              f"{'' if lbfgs else ', Adam only'}{', new-point score logged in training' if logged else ''})")
        print(f"  {'step':>6s} {'phase':6s} {'own pde':>10s} {'new pde':>10s} {'new/own':>9s}")
        for s in steps:
            model = load_checkpoint(d, None if s == final["step"] else s, device=device)
            e = by_step[s]
            pde = mean_r2(model, *pts, nu)
            if logged:
                log_diff.append(abs(e["loss_pde_fresh"] / pde - 1))
                pde = e["loss_pde_fresh"]
            ratio_check.append(mean_r2(model, *pts_check, nu) / pde)
            fresh["step"].append(s)
            fresh["pde"].append(sig3(pde))
            fresh["loss"].append(sig3(w["pde"] * pde + w["ic"] * e["loss_ic"] + w["bc"] * e["loss_bc"]))
            print(f"  {s:6d} {e['phase']:6s} {e['loss_pde']:10.3e} {pde:10.3e} {pde / e['loss_pde']:9.3g}")

        # final.pt: recomputed error must match the log; where is the jump at t = 1?
        model = load_checkpoint(d, device=device)
        ref = load_reference(ROOT / reference_path(round(nu * math.pi, 6)))
        err = rel_l2_grid(model, ref)
        jump = jump_position(model)
        check(f"{err:.3g}" == f"{final['rel_l2']:.3g}",
              f"rel_l2 at final.pt {err:.4g} vs logged {final['rel_l2']:.4g}")
        if logged:
            check(max(log_diff) < 0.02, f"logged new-point PDE vs recomputed: largest difference "
                                        f"{100 * max(log_diff):.2f}%")
        ratios = [p / by_step[s]["loss_pde"] for s, p in zip(fresh["step"], fresh["pde"])]
        early = [r for s, r in zip(fresh["step"], ratios) if s <= SWITCH]
        if sampling in ("uniform", "resample"):
            check(all(1 / 3 <= r <= 3 for r in early),
                  f"new/own PDE up to step {SWITCH}: {min(early):.2f} to {max(early):.2f}")
        else:
            print(f"  info  new/own PDE up to step {SWITCH}: {min(early):.2f} to {max(early):.2f} "
                  "(own points packed where the residual is large)")
        if sampling == "shock" and d.name.startswith("nu0.003"):
            check(0.6 <= ratios[-1] <= 1.0, f"final new/own PDE {ratios[-1]:.2f} (expected about 0.7-0.9)")
        if d.name == "nu0.003_vanilla_s2":
            check(3 <= fresh["pde"][-1] <= 12, f"final new-point PDE {fresh['pde'][-1]:.3g} (expected about 6)")
        worst = max(ratio_check, key=lambda r: abs(math.log(r)))
        check(1 / 3 < worst < 3, f"second point set (seed {CHECK_SEED}): largest change x{worst:.2f}, "
              f"final new-point PDE {fresh['pde'][-1]:.3g} vs {fresh['pde'][-1] * ratio_check[-1]:.3g}")
        print(f"  info  final new/own PDE {ratios[-1]:.3g}, error {final['rel_l2']:.3g}, "
              f"jump at t = 1: x = {jump:+.3f}")

        runs.append({
            "name": d.name,
            "nu_pi": round(nu * math.pi, 6),
            "sampling": sampling,
            "seed": cfg["seed"],
            "adam_steps": cfg["adam_steps"],
            "lbfgs": lbfgs,
            "step": [e["step"] for e in hist],
            "loss": [float(f"{e['loss_total']:.4g}") for e in hist],
            "loss_pde": [float(f"{e['loss_pde']:.4g}") for e in hist],
            "err": [float(f"{e['rel_l2']:.4g}") for e in hist],
            "fresh": fresh,
            "jump_x": round(jump, 3),
        })

    if failures:
        print(f"\n{len(failures)} sanity check(s) failed; runs.json NOT written:")
        for f in failures:
            print("  - " + f)
        raise SystemExit(1)

    out = ROOT / "data" / "loss_truth" / "runs.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "fresh_points": {"n": FRESH_N, "seed": FRESH_SEED, "x": [-1, 1], "t": [0, 1]},
        "runs": runs,
    }, separators=(",", ":")))
    print(f"\nall sanity checks passed\n{len(runs)} runs -> {out.relative_to(ROOT)} "
          f"({out.stat().st_size / 1e3:.0f} kB)")


if __name__ == "__main__":
    main()
