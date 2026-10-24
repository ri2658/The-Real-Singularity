"""Reference solution and error metric for the Burgers' benchmark.

Two implementations of the Cole-Hopf solution for u(x, 0) = -sin(pi x):

    burgers_exact        Gauss-Hermite quadrature, n = 200 (from Michelle's notebook).
    burgers_exact_trapz  Trapezoid rule over the full eta range that matters, log-sum-exp.
                         This is the default used by make_reference.

Validation (256-point x grid, t = 0.25 / 0.5 / 1.0), against an independent
finite-difference solve of the PDE (8192 cells, RK4) and against itself at 2x resolution:

    burgers_exact_trapz: self-convergence ~1e-16, matches the FD solver to <= 2e-5
                         at nu = 0.01/pi, 0.003/pi and 0.001/pi   -> safe as ground truth
    burgers_exact (Hermite), compared with the trapezoid version:
        nu = 0.01/pi    ~1e-16                    -> fine
        nu = 0.003/pi   ~1e-16                    -> fine
        nu = 0.001/pi   2.5e-3 at t=0.5, 3.4e-2 at t=1.0   -> NOT accurate enough

Why Hermite fails at small nu: the integrand peaks where the characteristic through
(x, t) starts, i.e. at |eta| up to ~t, but Hermite nodes only reach |eta| ~ 2*sqrt(nu*t)*20,
which falls short once nu is small. The trapezoid version integrates far enough
that everything beyond it is < e^-40 of the peak.

`rel_l2_grid` is also from Michelle's notebook.

Usage (generate the reference files for the week-4 nu sweep):
    python -m pinn.reference                 # nu = 0.01/pi, 0.003/pi, 0.001/pi
"""

import math
from pathlib import Path

import numpy as np
import torch

NU_BENCHMARK = 0.01 / math.pi
REF_DIR = Path("data/reference")
DEFAULT_REF_PATH = REF_DIR / "burgers_nu0.01pi.npz"


def reference_path(nu_pi: float) -> Path:
    """File name for nu = nu_pi / pi, e.g. 0.003 -> data/reference/burgers_nu0.003pi.npz."""
    return REF_DIR / f"burgers_nu{nu_pi:g}pi.npz"


def burgers_exact(x, t, nu, n=200):
    """Cole-Hopf solution via Gauss-Hermite quadrature. Accurate for nu >= 0.003/pi only."""
    z, w = np.polynomial.hermite.hermgauss(n)
    x = np.asarray(x, dtype=np.float64)[:, None]
    y = x - 2.0 * np.sqrt(nu * t) * z[None, :]
    logf = -np.cos(np.pi * y) / (2.0 * np.pi * nu)
    logf -= logf.max(axis=1, keepdims=True)  # avoids overflow for small nu
    f = np.exp(logf)
    return (-np.sin(np.pi * y) * f * w).sum(axis=1) / (f * w).sum(axis=1)


def burgers_exact_trapz(x, t, nu, refine=1.0, chunk=64):
    """Cole-Hopf solution via the trapezoid rule over the full relevant eta range.

        u(x, t) = - int sin(pi (x - eta)) F(eta) d eta / int F(eta) d eta
        log F(eta) = -cos(pi (x - eta)) / (2 pi nu) - eta^2 / (4 nu t)

    Range: |eta| <= W with W^2 = 4t/pi + 160 nu t, so that log F(W) is at least 40 below
    any value log F can take inside. Step: 1/40 of the narrowest feature width,
    min(sqrt(2 nu t), sqrt(nu)). `refine` > 1 shrinks the step (for convergence checks).
    """
    x = np.asarray(x, dtype=np.float64)
    if t <= 0:
        return -np.sin(np.pi * x)
    W = math.sqrt(4.0 * t / math.pi + 160.0 * nu * t) + 0.05
    h = min(math.sqrt(2.0 * nu * t), math.sqrt(nu)) / (40.0 * refine)
    eta = np.arange(-W, W + h, h)
    out = np.empty_like(x)
    for i in range(0, len(x), chunk):
        y = x[i:i + chunk, None] - eta[None, :]
        lg = -np.cos(np.pi * y) / (2.0 * np.pi * nu) - eta[None, :] ** 2 / (4.0 * nu * t)
        lg -= lg.max(axis=1, keepdims=True)
        f = np.exp(lg)
        out[i:i + chunk] = (-np.sin(np.pi * y) * f).sum(axis=1) / f.sum(axis=1)
    return out


def make_reference(nu=NU_BENCHMARK, nx=256, nt=100, t_min=0.01, t_max=1.0, method="trapz"):
    """Exact solution on a regular grid.

    Returns {"x": (nx,), "t": (nt,), "U": (nx, nt), "nu": float}, with U[i, j] = u(x[i], t[j]).
    Default grid matches the one Michelle used for the 0.067 baseline.
    """
    solver = {"trapz": burgers_exact_trapz, "hermite": burgers_exact}[method]
    x = np.linspace(-1.0, 1.0, nx)
    t = np.linspace(t_min, t_max, nt)
    U = np.stack([solver(x, tj, nu) for tj in t], axis=1)
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
    for nu_pi in (0.01, 0.003, 0.001):
        ref = make_reference(nu=nu_pi / math.pi)
        path = save_reference(ref, reference_path(nu_pi))
        print(f"saved {path}  U{ref['U'].shape}")
