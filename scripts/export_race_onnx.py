"""Export one PINN per viscosity to ONNX for the race page (week 6).

Same runs as the viscosity page's uniform-sampling row, so the two pages agree:
    nu = 0.01/pi   p1000_8x20_s1        (also the live PINN page's model)
    nu = 0.003/pi  nu0.003_vanilla_s0   (median of 3 seeds)
    nu = 0.001/pi  nu0.001_vanilla_s0   (median of 3 seeds)

Writes data/race_pinn/pinn_nu{0.01,0.003,0.001}pi.onnx and data/race_pinn/index.json
(run name, training wall time, rel L2). build_site.py copies them to site/data/race_pinn/.

Model format matches site/pinn/pinn.onnx: inputs x, t (float32, [N, 1]), output u ([N, 1]).

Checks (stops if one fails):
  1. ONNX Runtime matches PyTorch to < 1e-5 on the full 256 x 100 reference grid
     (the week-5 "done when" for the ONNX export).
  2. rel L2 against the reference matches the run's summary.json.

Run from the repo root (needs torch and onnxruntime):
    python3 scripts/export_race_onnx.py
"""

import json
import math
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pinn import load_reference, reference_path  # noqa: E402
from pinn.runlog import load_checkpoint  # noqa: E402

OUT = ROOT / "data" / "race_pinn"
RUNS = {0.01: "p1000_8x20_s1", 0.003: "nu0.003_vanilla_s0", 0.001: "nu0.001_vanilla_s0"}


def main():
    import onnxruntime as ort

    OUT.mkdir(parents=True, exist_ok=True)
    index = {}
    print(f"{'nu':>6s}  {'run':20s} {'max|torch-onnx|':>16s} {'rel L2 onnx':>12s} {'summary':>9s} {'train time':>10s}")
    for nu_pi, name in RUNS.items():
        run_dir = ROOT / "runs" / name
        cfg = json.loads((run_dir / "config.json").read_text())
        summ = json.loads((run_dir / "summary.json").read_text())
        assert abs(cfg["nu"] * math.pi - nu_pi) < 1e-9, (name, cfg["nu"])
        model = load_checkpoint(run_dir)

        path = OUT / f"pinn_nu{nu_pi:g}pi.onnx"
        torch.onnx.export(
            model, (torch.zeros(1, 1), torch.zeros(1, 1)), str(path), dynamo=False,
            input_names=["x", "t"], output_names=["u"],
            dynamic_axes={"x": {0: "batch"}, "t": {0: "batch"}, "u": {0: "batch"}},
            opset_version=17,
        )

        # Full reference grid, same point order as the race page: row j = time t[j].
        ref = load_reference(reference_path(nu_pi))           # U is (nx, nt)
        T, X = np.meshgrid(ref["t"], ref["x"], indexing="ij")  # (nt, nx)
        xs = X.reshape(-1, 1).astype(np.float32)
        ts = T.reshape(-1, 1).astype(np.float32)
        with torch.no_grad():
            u_torch = model(torch.from_numpy(xs), torch.from_numpy(ts)).numpy()
        sess = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
        u_onnx = sess.run(None, {"x": xs, "t": ts})[0]

        gap = float(np.max(np.abs(u_torch - u_onnx)))
        U = ref["U"].T.reshape(-1, 1)                           # (nt*nx, 1) in the same order
        err = float(np.linalg.norm(u_onnx - U) / np.linalg.norm(U))
        print(f"{nu_pi:6g}  {name:20s} {gap:16.2e} {err:12.3e} {summ['final_rel_l2']:9.3e} {summ['wall_time_s'] / 60:8.1f} min")
        if gap > 1e-5:
            raise SystemExit(f"{name}: ONNX differs from PyTorch by {gap:.2e} (> 1e-5)")
        if abs(err - summ["final_rel_l2"]) > 1e-3 * summ["final_rel_l2"]:
            raise SystemExit(f"{name}: rel L2 {err:.4e} != summary {summ['final_rel_l2']:.4e}")

        index[f"nu{nu_pi:g}pi"] = {"run": name, "file": path.name, "rel_l2": round(err, 6),
                                   "train_seconds": summ["wall_time_s"]}

    (OUT / "index.json").write_text(json.dumps(index, indent=1))
    print(f"\nwrote {len(RUNS)} models + index.json to {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
