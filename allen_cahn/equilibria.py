"""Five Allen-Cahn equilibria by Newton's method (week 5, task 1).

u_t = u_xx + mu (u - u^3) on (0, pi), u(0) = u(pi) = 0, mu = 6, N = 128.
Discrete: F(U) = L U + mu (U - U^3) = 0 on the 127 interior points.
Writes data/allen_cahn/equilibria.json.
"""
import json
from pathlib import Path

import numpy as np

MU = 6.0
N = 128
H = np.pi / N
X = np.linspace(H, np.pi - H, N - 1)          # 127 interior points
L = (np.diag(-2.0 * np.ones(N - 1)) + np.diag(np.ones(N - 2), 1)
     + np.diag(np.ones(N - 2), -1)) / H**2   # Dirichlet Laplacian


def F(U):
    return L @ U + MU * (U - U**3)


def jacobian(U):
    return L + MU * np.diag(1.0 - 3.0 * U**2)


def newton(U0, tol=1e-12, maxit=50):
    U = U0.copy()
    for it in range(maxit):
        r = F(U)
        if np.max(np.abs(r)) <= tol:
            break
        U -= np.linalg.solve(jacobian(U), r)
    return U, it


def energy(U):
    """E_h = h*sum(1/2 ((U_{j+1}-U_j)/h)^2) - h*sum(mu (U^2/2 - U^4/4)), U_0 = U_N = 0."""
    Ub = np.concatenate(([0.0], U, [0.0]))
    grad = 0.5 * np.sum(np.diff(Ub) ** 2) / H
    pot = H * np.sum(MU * (U**2 / 2 - U**4 / 4))
    return grad - pot


def top_eigs(U, k=3):
    ev = np.linalg.eigvalsh(jacobian(U))      # symmetric
    return np.sort(ev)[::-1][:k]


def main():
    starts = {"zero": 0 * X, "hump": 1.0 * np.sin(X), "S": 1.0 * np.sin(2 * X)}
    states, info = {}, {}
    for name, U0 in starts.items():
        U, it = newton(U0)
        states[name] = U
        info[name] = it
    states["minus_hump"] = -states["hump"]
    states["minus_S"] = -states["S"]

    out = {"mu": MU, "N": N, "h": H, "x": X.tolist(), "states": {}}
    print(f"{'state':11s} {'energy':>9s} {'max|U|':>7s} {'residual':>9s}  top-3 eigenvalues")
    for name in ["zero", "hump", "minus_hump", "S", "minus_S"]:
        U = states[name]
        E, res, ev = energy(U), np.max(np.abs(F(U))), top_eigs(U)
        out["states"][name] = {"U": U.tolist(), "energy": E, "max_abs": float(np.max(np.abs(U))),
                               "residual": float(res), "top_eigenvalues": ev.tolist()}
        print(f"{name:11s} {E:9.4f} {np.max(np.abs(U)):7.4f} {res:9.1e}  "
              + ", ".join(f"{v:8.3f}" for v in ev))
    print("Newton iterations:", info)

    path = Path(__file__).resolve().parents[1] / "data/allen_cahn/equilibria.json"
    path.write_text(json.dumps(out, indent=1))
    print("wrote", path)


if __name__ == "__main__":
    main()
