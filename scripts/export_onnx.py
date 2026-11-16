"""Export runs/p1000_8x20_s1/final.pt and check ONNX Runtime against PyTorch.

Run from the repo root:
    python scripts/export_onnx.py
"""

import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pinn.model import PINN

RUN = ROOT / "runs" / "p1000_8x20_s1"
OUT = ROOT / "web" / "pinn.onnx"


def load_model():
    model = PINN(depth=8, width=20, init="xavier")
    state = torch.load(RUN / "final.pt", map_location="cpu", weights_only=True)
    model.load_state_dict(state)
    model.eval()
    return model


def export(model):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    x = torch.zeros(1, 1)
    t = torch.zeros(1, 1)
    torch.onnx.export(
        model,
        (x, t),
        OUT,
        dynamo=False,
        input_names=["x", "t"],
        output_names=["u"],
        dynamic_axes={"x": {0: "batch"}, "t": {0: "batch"}, "u": {0: "batch"}},
        opset_version=17,
    )


def check(model):
    import onnxruntime as ort

    session = ort.InferenceSession(str(OUT), providers=["CPUExecutionProvider"])
    # A batch of 1 and a batch of 4, so the dynamic axis is actually used.
    batches = [1, 4]
    worst = 0.0
    for n in batches:
        x = torch.linspace(-1, 1, n).view(n, 1)
        t = torch.full((n, 1), 0.5)
        with torch.no_grad():
            pytorch = model(x, t).numpy()
        onnx = session.run(None, {"x": x.numpy().astype(np.float32), "t": t.numpy().astype(np.float32)})[0]
        gap = float(np.max(np.abs(pytorch - onnx)))
        worst = max(worst, gap)
        print(f"batch {n}: max |pytorch - onnx| = {gap:.3e}")
    if worst > 1e-5:
        raise SystemExit(f"ONNX output does not match PyTorch (max gap {worst:.3e})")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    model = load_model()
    export(model)
    check(model)
