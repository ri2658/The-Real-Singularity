"""Reference solution and error metric for the Burgers' benchmark.

`burgers_exact` and `rel_l2_grid` are taken from Michelle's notebook
(notebooks/burgers_pinn_reference calculation and L2.ipynb, branch michelleZhao).

Accuracy of `burgers_exact` (Gauss-Hermite, n = 200), measured against brute-force
quadrature on a 256-point x grid:
    nu = 0.01/pi   relative error ~1e-16 for all t        -> safe as ground truth
    nu = 0.003/pi  ~2e-3 at t = 0.5, ~1e-2 at t = 1.0     -> NOT accurate enough
    nu = 0.001/pi  ~0.1 at t = 0.5,  ~0.3 at t = 1.0      -> unusable
For the week-4 nu sweep a different reference method is needed.

Usage (generate the reference file):
    python -m pinn.reference
"""

import math
import warnings
from pathlib import Path

import numpy as np
import torch

NU_BENCHMARK = 0.01 / math.pi
DEFAULT_REF_PATH = Path("data/reference/burgers_nu0.01pi.npz")


def burgers_exact(x, t, nu, n=200):
    """Cole-Hopf solution for u(x, 0) = -sin(pi x). x: 1D array, t: scalar >= 0."""
    z, w = np.polynomial.hermite.hermgauss(n)
    x = np.asarray(x, dtype=np.float64)[:, None]
    y = x - 2.0 * np.sqrt(nu * t) * z[None, :]
    logf = -np.cos(np.pi * y) / (2.0 * np.pi * nu)
    logf -= logf.max(axis=1, keepdims=True)  # avoids overflow for small nu
    f = np.exp(logf)
    return (-np.sin(np.pi * y) * f * w).sum(axis=1) / (f * w).sum(axis=1)


def make_reference(nu=NU_BENCHMARK, nx=256, nt=100, t_min=0.01, t_max=1.0):
    """Exact solution on a regular grid.

    Returns {"x": (nx,), "t": (nt,), "U": (nx, nt), "nu": float}, with U[i, j] = u(x[i], t[j]).
    Default grid matches the one Michelle used for the 0.067 baseline.
    """
    if nu < NU_BENCHMARK * (1 - 1e-9):
        warnings.warn(
            f"burgers_exact is not accurate for nu = {nu:.3g} < 0.01/pi; "
            "do not use this reference as ground truth.",
            stacklevel=2,
        )
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
    d = np.load(path)
    return {"x": d["x"], "t": d["t"], "U": d["U"], "nu": float(d["nu"])}


def rel_l2_grid(model, ref) -> float:
    """Relative L2 error ||u_pred - u_ref|| / ||u_ref|| over the whole reference grid.

    This is the official week-3 metric (target ~1e-3).
    """
    X, T = np.meshgrid(ref["x"], ref["t"], indexing="ij")  # both (nx, nt)
    device = next(model.parameters()).device
    x = torch.tensor(X.reshape(-1, 1), dtype=torch.float32, device=device)
    t = torch.tensor(T.reshape(-1, 1), dtype=torch.float32, device=device)
    was_training = model.training
    model.eval()
    with torch.no_grad():
        u = model(x, t).cpu().numpy().reshape(X.shape)
    model.train(was_training)
    U = ref["U"]
    return float(np.linalg.norm(u - U) / np.linalg.norm(U))


if __name__ == "__main__":
    ref = make_reference()
    path = save_reference(ref)
    print(f"saved {path}  x{ref['x'].shape} t{ref['t'].shape} U{ref['U'].shape}")
