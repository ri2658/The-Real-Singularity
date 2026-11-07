"""Export training histories for the loss-vs-truth page.

Collects the week-3 baseline runs (p1000_8x20_s0..s4) and the week-4 sweep runs
(nu{0.01,0.003,0.001}_{vanilla,shock}_s{0,1,2}) and writes, for each run,
its viscosity, sampling, seed and the logged (step, training loss, true error).

Output: data/loss_truth/runs.json (copied into site/data/ by build_site.py).

Run from the repo root:
    python scripts/export_loss_truth.py
"""

import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN_NAME = re.compile(r"^(p1000_8x20_s\d|nu0\.\d+_(vanilla|shock)_s\d)$")


def main():
    runs = []
    for d in sorted((ROOT / "runs").iterdir()):
        if not RUN_NAME.match(d.name):
            continue
        cfg = json.loads((d / "config.json").read_text())
        hist = json.loads((d / "history.json").read_text())
        runs.append({
            "name": d.name,
            "nu_pi": round(cfg["nu"] * math.pi, 6),
            "sampling": cfg.get("sampling", "uniform"),
            "seed": cfg["seed"],
            "step": [e["step"] for e in hist],
            "loss": [float(f"{e['loss_total']:.4g}") for e in hist],
            "err": [float(f"{e['rel_l2']:.4g}") for e in hist],
        })
        print(f"{d.name:22s} nu={runs[-1]['nu_pi']:g}/pi {runs[-1]['sampling']:8s} "
              f"final loss {hist[-1]['loss_total']:.2e}  error {hist[-1]['rel_l2']:.2e}")

    out = ROOT / "data" / "loss_truth" / "runs.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"runs": runs}, separators=(",", ":")))
    print(f"\n{len(runs)} runs -> {out.relative_to(ROOT)} ({out.stat().st_size / 1e3:.0f} kB)")


if __name__ == "__main__":
    main()
