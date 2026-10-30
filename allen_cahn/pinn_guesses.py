"""Deliberately under-trained PINN guesses for steady Allen-Cahn (week 5, task 3).

u'' + mu (u - u^3) = 0 on (0, pi), u(0) = u(pi) = 0, mu = 6.
Same pattern as pinn/ (tanh MLP, residual by autograd, weighted loss, Adam loop), but 1D steady,
with hard BCs and symmetry by construction (s = x - pi/2, g = MLP):
    hump: u = sin(x) * g(s^2)        S: u = sin(x) * s * g(s^2)
Loss = mean(r^2) + W_AMP * relu(c - mean(u^2))^2, c = half the exact state's mean(U^2).
zero_guess = hump ansatz without the amplitude term (Demo 2d: low loss, wrong answer).
Network size, points and lr are the task defaults (the notes don't give them); W_AMP is set so the
guesses match the notes' rough accuracy (Table 2), not to be accurate.
Writes data/allen_cahn/pinn_guesses.json and allen_cahn/pinn_guesses.png.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn

from equilibria import MU, N, X, F

DATA = Path(__file__).resolve().parents[1] / "data/allen_cahn"
SEED = 0
WIDTH, DEPTH = 20, 2
N_COL = 200
ADAM_STEPS = 2000
LR = 1e-3
# Needs W*c > ~40 to beat the residual's pull toward u = 0. Larger W also slows Adam's approach to the
# solution; 1e4 gives the notes' rough-guess accuracy (hump ~1.6e-2, S ~4.4e-2) in 2,000 steps.
W_AMP = 1e4


class Ansatz(nn.Module):
    def __init__(self, kind):
        super().__init__()
        layers, d_in = [], 1
        for _ in range(DEPTH):
            layers += [nn.Linear(d_in, WIDTH), nn.Tanh()]
            d_in = WIDTH
        layers.append(nn.Linear(WIDTH, 1))
        self.g = nn.Sequential(*layers)
        self.kind = kind

    def forward(self, x):
        s = x - np.pi / 2
        u = torch.sin(x) * self.g(s**2)
        return u * s if self.kind == "S" else u


def residual(model, x):
    x = x.detach().clone().requires_grad_(True)
    u = model(x)
    u_x = torch.autograd.grad(u, x, torch.ones_like(u), create_graph=True)[0]
    u_xx = torch.autograd.grad(u_x, x, torch.ones_like(u_x), create_graph=True)[0]
    return u_xx + MU * (u - u**3), u


def train(kind, c):
    """c = amplitude target, or None for no amplitude term. Returns (model, final loss)."""
    torch.manual_seed(SEED)
    model = Ansatz(kind)
    x = torch.linspace(0, np.pi, N_COL + 2)[1:-1].reshape(-1, 1)
    opt = torch.optim.Adam(model.parameters(), lr=LR)
    for step in range(ADAM_STEPS + 1):
        opt.zero_grad()
        r, u = residual(model, x)
        loss = torch.mean(r**2)
        if c is not None:
            loss = loss + W_AMP * torch.relu(c - torch.mean(u**2)) ** 2
        if step == ADAM_STEPS:      # loss at the final weights, no update
            break
        loss.backward()
        opt.step()
    return model, float(loss.item())


def evaluate(model, x):
    with torch.no_grad():
        return model(torch.tensor(x, dtype=torch.float32).reshape(-1, 1)).numpy().ravel().astype(np.float64)


def main():
    eq = json.loads((DATA / "equilibria.json").read_text())
    x = np.array(eq["x"])
    assert np.array_equal(x, X)
    exact = {k: np.array(eq["states"][k]["U"]) for k in ("zero", "hump", "S")}

    runs = {"hump_guess": ("hump", "hump", 0.5 * np.mean(exact["hump"] ** 2)),
            "S_guess": ("S", "S", 0.5 * np.mean(exact["S"] ** 2)),
            "zero_guess": ("hump", "zero", None)}
    targets = {"hump_guess": "~1.6e-2", "S_guess": "~4.4e-2", "zero_guess": "tiny"}

    out = {"mu": MU, "N": N, "x": x.tolist()}
    guesses = {}
    print(f"{'run':10s} {'sup|U-exact|':>12s} {'target':>8s} {'loss':>9s} {'sym err':>9s} "
          f"{'max|F(U)|':>9s} {'max|U|':>9s}")
    for name, (kind, ref, c) in runs.items():
        model, loss = train(kind, c)
        U = evaluate(model, x)
        U_mirror = evaluate(model, np.pi - x)
        # The ansatz allows both signs; u -> -u maps solutions to solutions, so a run that
        # lands on -ref is flipped (and recorded) rather than retrained.
        flipped = ref != "zero" and np.max(np.abs(U + exact[ref])) < np.max(np.abs(U - exact[ref]))
        if flipped:
            U, U_mirror = -U, -U_mirror
        sym = np.max(np.abs(U + U_mirror)) if kind == "S" else np.max(np.abs(U - U_mirror))
        err = float(np.max(np.abs(U - exact[ref])))
        res = float(np.max(np.abs(F(U))))
        guesses[name] = (U, ref)
        out[name] = U.tolist()
        out[name + "_info"] = {"exact_state": ref, "sup_err": err, "final_loss": loss,
                               "adam_steps": ADAM_STEPS, "amplitude_c": c, "amplitude_w": W_AMP if c else None,
                               "sign_flipped": bool(flipped),
                               "symmetry_err": float(sym), "discrete_residual": res}
        print(f"{name:10s} {err:12.2e} {targets[name]:>8s} {loss:9.2e} {sym:9.1e} "
              f"{res:9.2e} {np.max(np.abs(U)):9.2e}" + ("  (sign flipped)" if flipped else ""))

    path = DATA / "pinn_guesses.json"
    path.write_text(json.dumps(out, indent=1))
    print("wrote", path)

    fig, axes = plt.subplots(1, 3, figsize=(13, 3.6))
    for ax, (name, (U, ref)) in zip(axes, guesses.items()):
        ax.plot(x, exact[ref], "k-", lw=2, label=f"exact {ref}")
        ax.plot(x, U, "r--", lw=1.5, label=name)
        ax.set_title(f"{name}: sup err {np.max(np.abs(U - exact[ref])):.1e}")
        ax.set_xlabel("x")
        ax.legend(fontsize=8)
    axes[0].set_ylabel("u")
    fig.tight_layout()
    png = Path(__file__).resolve().parent / "pinn_guesses.png"
    fig.savefig(png, dpi=120)
    print("wrote", png)


if __name__ == "__main__":
    main()
