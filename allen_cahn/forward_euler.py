"""Forward-Euler reference for Allen-Cahn (week 5, task 2) -- answer key for the JS simulator.

u_t = u_xx + mu (u - u^3) on (0, pi), u(0) = u(pi) = 0, mu = 6, N = 128.
Update: U <- U + dt * F(U), dt = 0.4 h^2. Grid, L, F and energy come from equilibria.py;
the equilibria themselves are read from data/allen_cahn/equilibria.json.
Writes data/allen_cahn/euler_check.json.
"""
import json
from pathlib import Path

import numpy as np

from equilibria import MU, N, H, X, F, energy

DT = 0.4 * H**2
DATA = Path(__file__).resolve().parents[1] / "data/allen_cahn"
SNAP_TIMES = [0.0, 0.1, 0.5, 1.0]
SNAP_TIMES_S = SNAP_TIMES + [3.0, 5.0, 10.0]   # S run: also capture the slide to the hump


def nsteps(t):
    return int(round(t / DT))


def run(U0, t_end, ref=None):
    """Integrate to t_end. Returns final U, per-step sup-norm distance to ref, and per-step energy."""
    U = U0.copy()
    n = nsteps(t_end)
    dev = np.empty(n + 1)
    E = np.empty(n + 1)
    dev[0] = np.max(np.abs(U - ref)) if ref is not None else 0.0
    E[0] = energy(U)
    for k in range(1, n + 1):
        U = U + DT * F(U)
        dev[k] = np.max(np.abs(U - ref)) if ref is not None else 0.0
        E[k] = energy(U)
    return U, dev, E


def fit_rate(dev, t0, t1):
    """Slope of log(dev) vs t over [t0, t1]."""
    k = np.arange(nsteps(t0), nsteps(t1) + 1)
    return np.polyfit(k * DT, np.log(dev[k]), 1)[0]


def escape_time(S, eps, thresh=0.1, t_max=40.0):
    U = S + eps * np.sin(X)
    for k in range(1, nsteps(t_max) + 1):
        U = U + DT * F(U)
        if np.max(np.abs(U - S)) > thresh:
            return k * DT
    return np.nan


def snapshots(U0, times=SNAP_TIMES):
    out, U, k = [], U0.copy(), 0
    for t in times:
        while k < nsteps(t):
            U = U + DT * F(U)
            k += 1
        out.append({"t": t, "steps": k, "U": U.tolist(), "E_h": energy(U)})
    return out


def main():
    eq = json.loads((DATA / "equilibria.json").read_text())
    hump = np.array(eq["states"]["hump"]["U"])
    S = np.array(eq["states"]["S"]["U"])
    print(f"mu={MU} N={N} h={H:.6f} dt={DT:.4e} ({1 / DT:.0f} steps per time unit)")

    # 1. perturbed hump heals
    _, dev_h, E_h = run(hump + 0.1 * np.sin(3 * X), 2.5, ref=hump)
    rate_h = fit_rate(dev_h, 1.0, 2.5)
    print(f"[1] hump+0.1 sin3x: decay rate {-rate_h:.4f}  (target 8.69), "
          f"shrink/time {np.exp(-rate_h):.0f}x, ||U-hump|| at t=2.5: {dev_h[-1]:.2e}")

    # 2. perturbed S leaves and settles at +hump
    U_s, dev_s, E_s = run(S + 1e-3 * np.sin(X), 10.0, ref=S)
    rate_s = fit_rate(dev_s, 1.0, 2.5)
    to_hump = np.max(np.abs(U_s - hump))
    print(f"[2] S+1e-3 sin x: growth rate {rate_s:.4f}  (target 1.529), "
          f"||U-hump|| at t=10: {to_hump:.2e}")

    # 3. energy monotone
    dE_h, dE_s = np.max(np.diff(E_h)), np.max(np.diff(E_s))
    print(f"[3] max energy increase per step: hump run {dE_h:.2e}, S run {dE_s:.2e}  (target <= 0)")

    # 4. escape time vs eps
    eps_list = [10.0**-p for p in range(2, 9)]
    T = np.array([escape_time(S, e) for e in eps_list])
    slope = np.polyfit(-np.log10(eps_list), T, 1)[0]
    print("[4] escape times:", ", ".join(f"1e-{p}:{t:.3f}" for p, t in zip(range(2, 9), T)))
    print(f"    slope per decade {slope:.4f}  (target 1.5056)")

    out = {"mu": MU, "N": N, "h": H, "dt": DT, "x": X.tolist(), "runs": {
        "hump_pert": {"formula": "hump + 0.1*sin(3x)",
                      "snapshots": snapshots(hump + 0.1 * np.sin(3 * X))},
        "S_pert": {"formula": "S + 1e-3*sin(x)",
                   "snapshots": snapshots(S + 1e-3 * np.sin(X), SNAP_TIMES_S)},
    }}
    path = DATA / "euler_check.json"
    path.write_text(json.dumps(out, indent=1))
    print("wrote", path)


if __name__ == "__main__":
    main()
