"""Reference solution and error metric for the Burgers benchmark.

`rel_l2_grid` matches the week-3 metric. `burgers_exact` is the Cole-Hopf
formula for u(x, 0) = -sin(pi x). The previous Gauss-Hermite rule (n = 200)
is accurate only at nu = 0.01/pi. This version integrates the same formula
on a grid fine enough to resolve the thin peaks at smaller viscosities.

Checked against Gauss-Hermite n = 200 at nu = 0.01/pi (relative difference
~1e-16) and against scipy.integrate.quad at nu = 0.001/pi, t = 1 (absolute
difference ~1e-15). Doubling the grid changes results by ~1e-16 down through
nu = 0.0001/pi.

Usage, from the repo root:
    python -m pinn.reference
"""

import math
from pathlib import Path

import numpy as np
import torch

NU_BENCHMARK = 0.01 / math.pi
DEFAULT_REF_PATH = Path("data/reference/burgers_nu0.01pi.npz")
# Viscosities for the combined tutorial and quarter-plan sweep.
SWEEP_NU = (
    (0.01 / math.pi, "0.01pi"),
    (0.003 / math.pi, "0.003pi"),
    (0.001 / math.pi, "0.001pi"),
    (0.0001 / math.pi, "0.0001pi"),
)


def burgers_exact(x, t, nu, n=200):
    """Cole-Hopf solution for u(x, 0) = -sin(pi x). x: 1D array, t: scalar >= 0.

    `n` is accepted so older calls still work. The grid is chosen from `nu`
    and is at least `n` points.
    """
    x = np.asarray(x, dtype=np.float64).reshape(-1)
    if t <= 1e-12:
        return -np.sin(np.pi * x)
    std = math.sqrt(2.0 * nu * t)
    # The heat kernel lives on the scale `std`. The initial-data weight is
    # period 2 and peaked with width ~sqrt(nu), so the window has to cover
    # the nearest peaks, not only a few kernel widths.
    length = max(12.0 * std, 2.0 + 6.0 * std)
    spacing = math.sqrt(nu) / 40.0
    m = max(int(math.ceil(2.0 * length / spacing)), int(n))
    eta = np.linspace(-length, length, m + 1)
    y = x[:, None] - eta[None, :]
    logf = -np.cos(np.pi * y) / (2.0 * np.pi * nu) - (eta * eta) / (4.0 * nu * t)
    logf -= np.max(logf, axis=1, keepdims=True)
    weight = np.exp(logf)
    trap = np.ones(eta.shape, dtype=np.float64)
    trap[0] = trap[-1] = 0.5
    numerator = (-np.sin(np.pi * y) * weight * trap).sum(axis=1)
    denominator = (weight * trap).sum(axis=1)
    return numerator / denominator


def make_reference(nu=NU_BENCHMARK, nx=256, nt=100, t_min=0.01, t_max=1.0):
    """Exact solution on a regular grid.

    Returns {"x": (nx,), "t": (nt,), "U": (nx, nt), "nu": float}, with U[i, j] = u(x[i], t[j]).
    Default grid matches the one used for the 0.067 baseline.
    """
    x = np.linspace(-1.0, 1.0, nx)
    t = np.linspace(t_min, t_max, nt)
    U = np.stack([burgers_exact(x, tj, nu) for tj in t], axis=1)
    return {"x": x, "t": t, "U": U, "nu": float(nu)}


def save_reference(ref, path=DEFAULT_REF_PATH):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(path, x=ref["x"], t=ref["t"], U=ref["U"], nu=ref["nu"])
    return path


def load_reference(path=DEFAULT_REF_PATH):
    data = np.load(path)
    return {"x": data["x"], "t": data["t"], "U": data["U"], "nu": float(data["nu"])}


def rel_l2_grid(model, ref) -> float:
    """Relative L2 error ||u_pred - u_ref|| / ||u_ref|| over the whole reference grid.

    This is the official week-3 metric (target ~1e-3).
    """
    X, T = np.meshgrid(ref["x"], ref["t"], indexing="ij")
    device = next(model.parameters()).device
    x = torch.tensor(X.reshape(-1, 1), dtype=torch.float32, device=device)
    t = torch.tensor(T.reshape(-1, 1), dtype=torch.float32, device=device)
    was_training = model.training
    model.eval()
    with torch.no_grad():
        u = model(x, t).cpu().numpy().reshape(X.shape)
    model.train(was_training)
    truth = ref["U"]
    return float(np.linalg.norm(u - truth) / np.linalg.norm(truth))


if __name__ == "__main__":
    for nu, label in SWEEP_NU:
        ref = make_reference(nu=nu)
        path = save_reference(ref, Path(f"data/reference/burgers_nu{label}.npz"))
        print(f"saved {path}  x{ref['x'].shape} t{ref['t'].shape} U{ref['U'].shape}")
