"""PINN checkpoints for steady Allen-Cahn (week 5, task 3, second experiment).

One honest run per state (hump, S): Adam 2000 steps (guess saved at 100, 200, 500, 1000, 2000), then
L-BFGS set up like pinn/train.py ("accurate"). Nothing is tuned to an error target: rough = an
early checkpoint. Same ansatz as pinn_rough_w1e4_adam2000.py, W_AMP = 100 (the minimum that keeps u off zero).

Also: Newton on N = 512 to measure the N = 128 answer key's own grid error, and a forward-Euler
stability check of every curve to t = 40.

Writes data/allen_cahn/pinn_accurate_w100_lbfgs.json, allen_cahn/pinn_accurate_w100_lbfgs.png and
runs/allen_cahn_pinn_accurate_w100_lbfgs/{hump,S}/ (config.json, history.json, ckpt_*.pt, final.pt).
"""
import json
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch

from equilibria import MU, N, X, F
from forward_euler import DT, nsteps
from pinn_rough_w1e4_adam2000 import Ansatz, residual

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pinn.runlog import RunLogger  # noqa: E402

DATA = ROOT / "data/allen_cahn"
RUNS = ROOT / "runs/allen_cahn_pinn_accurate_w100_lbfgs"

CFG = {
    "mu": MU, "depth": 2, "width": 20, "activation": "tanh", "dtype": "float32", "seed": 0,
    "n_col": 200, "amp_weight": 100.0, "amp_c": "0.5 * mean(U_newton128^2)",
    "loss": "loss_pde + amp_weight * loss_amp, loss_amp = relu(c - mean(u^2))^2 (unweighted)",
    "adam_steps": 2000, "lr": 1e-3, "checkpoints": [100, 200, 500, 1000, 2000],
    "lbfgs_steps": 15000, "lbfgs_history": 50, "lbfgs_patience": 200,
    "lbfgs": {"lr": 1.0, "max_iter": 1, "max_eval": 25, "tolerance_grad": 1e-12,
              "tolerance_change": 1e-15, "line_search_fn": "strong_wolfe"},
    "log_every": 50,
    "rel_l2": "||U - sign*U_newton128||_2 / ||U_newton128||_2 on the 127 grid points, "
              "sign = branch the run converged to (see reference_sign)",
}


# ---------------- Newton on a general grid ----------------

def newton_grid(n, U0, tol=1e-12, maxit=50):
    h = np.pi / n
    Lh = (np.diag(-2.0 * np.ones(n - 1)) + np.diag(np.ones(n - 2), 1)
          + np.diag(np.ones(n - 2), -1)) / h**2
    U = U0.copy()
    for _ in range(maxit):
        r = Lh @ U + MU * (U - U**3)
        if np.max(np.abs(r)) <= tol:
            break
        U -= np.linalg.solve(Lh + MU * np.diag(1.0 - 3.0 * U**2), r)
    return U


# ---------------- training ----------------

def grid_eval(model, x):
    with torch.no_grad():
        return model(torch.tensor(x, dtype=torch.float32).reshape(-1, 1)).numpy().ravel().astype(np.float64)


def losses(model, x_col, c):
    r, u = residual(model, x_col)
    pde = torch.mean(r**2)
    amp = torch.relu(c - torch.mean(u**2)) ** 2
    return pde, amp, pde + CFG["amp_weight"] * amp


def train(kind, c):
    """Adam then L-BFGS. Returns model, raw log entries (with grid U), checkpoint U's, L-BFGS info."""
    torch.manual_seed(CFG["seed"])
    model = Ansatz(kind)
    x_col = torch.linspace(0, np.pi, CFG["n_col"] + 2)[1:-1].reshape(-1, 1)
    entries, ckpts, ckpt_models = [], {}, {}

    def record(step, phase, pde, amp, total):
        entries.append({"step": step, "phase": phase, "loss_total": float(total.item()),
                        "loss_pde": float(pde.item()), "loss_amp": float(amp.item()),
                        "U": grid_eval(model, X)})

    opt = torch.optim.Adam(model.parameters(), lr=CFG["lr"])
    for step in range(CFG["adam_steps"] + 1):
        opt.zero_grad()
        pde, amp, total = losses(model, x_col, c)
        if step % CFG["log_every"] == 0 or step in CFG["checkpoints"]:
            record(step, "adam", pde, amp, total)
        if step in CFG["checkpoints"]:
            ckpts[step] = {"model_U": grid_eval(model, X), "model_U_mirror": grid_eval(model, np.pi - X),
                           "loss": float(total.item())}
            ckpt_models[step] = {k: v.clone() for k, v in model.state_dict().items()}
        if step == CFG["adam_steps"]:
            break
        total.backward()
        opt.step()

    lb = CFG["lbfgs"]
    lbfgs = torch.optim.LBFGS(model.parameters(), lr=lb["lr"], max_iter=lb["max_iter"],
                              max_eval=lb["max_eval"], history_size=CFG["lbfgs_history"],
                              tolerance_grad=lb["tolerance_grad"],
                              tolerance_change=lb["tolerance_change"],
                              line_search_fn=lb["line_search_fn"])

    def closure():
        lbfgs.zero_grad()
        _, _, total = losses(model, x_col, c)
        total.backward()
        return total

    best, since_best, reason = float("inf"), 0, "max iterations"
    k = 0
    for k in range(1, CFG["lbfgs_steps"] + 1):
        step = CFG["adam_steps"] + k
        value = float(lbfgs.step(closure).detach())
        if not math.isfinite(value):
            reason = f"non-finite loss ({value})"
            break
        if value < best * (1 - 1e-6):
            best, since_best = value, 0
        else:
            since_best += 1
        stalled = since_best >= CFG["lbfgs_patience"]
        if stalled:
            reason = f"no improvement for {CFG['lbfgs_patience']} iterations"
        if stalled or k == CFG["lbfgs_steps"] or step % CFG["log_every"] == 0:
            record(step, "lbfgs", *losses(model, x_col, c))
        if stalled:
            break
    _, _, total = losses(model, x_col, c)
    ckpts["accurate"] = {"model_U": grid_eval(model, X), "model_U_mirror": grid_eval(model, np.pi - X),
                         "loss": float(total.item())}
    info = {"lbfgs_iterations": k, "final_step": CFG["adam_steps"] + k, "stop_reason": reason}
    return model, entries, ckpts, ckpt_models, info


# ---------------- stability (forward Euler, N = 128) ----------------

def evolve(U0, kind, hump, S, t_max=40.0, tol=1e-3):
    U = U0.copy()
    if kind == "hump":
        if np.max(np.abs(U - hump)) < tol:
            return {"t_to_hump": 0.0}
        for k in range(1, nsteps(t_max) + 1):
            U = U + DT * F(U)
            if np.max(np.abs(U - hump)) < tol:
                return {"t_to_hump": k * DT}
        return {"t_to_hump": None}
    d_min, t_min = np.max(np.abs(U - S)), 0.0
    for k in range(1, nsteps(t_max) + 1):
        U = U + DT * F(U)
        d = np.max(np.abs(U - S))
        if d < d_min:
            d_min, t_min = d, k * DT
        for sgn, name in ((1, "+hump"), (-1, "-hump")):
            if np.max(np.abs(U - sgn * hump)) < tol:
                return {"min_dist_S": d_min, "t_min_dist_S": t_min, "settles_at": name, "t_settle": k * DT}
    return {"min_dist_S": d_min, "t_min_dist_S": t_min, "settles_at": "never", "t_settle": None}


# ---------------- main ----------------

def main():
    eq = json.loads((DATA / "equilibria.json").read_text())
    x = np.array(eq["x"])
    assert np.array_equal(x, X)
    U128 = {k: np.array(eq["states"][k]["U"]) for k in ("hump", "S")}

    # grid floor: N = 512 Newton, sampled at every 4th interior point
    x512 = np.linspace(np.pi / 512, np.pi - np.pi / 512, 511)
    dx = float(np.max(np.abs(x512[3::4] - x)))
    assert dx < 1e-14, dx
    U512, floor = {}, {}
    for k in ("hump", "S"):
        U0 = np.interp(x512, np.r_[0.0, x, np.pi], np.r_[0.0, U128[k], 0.0])
        U512[k] = newton_grid(512, U0)[3::4]
        floor[k] = float(np.max(np.abs(U128[k] - U512[k])))
    print(f"N=512 every-4th x vs N=128 x: max diff {dx:.1e}")
    print("\n[1] Grid floor sup|U128 - U512[3::4]|")
    print(f"    {'state':6s} {'floor':>9s}")
    for k in ("hump", "S"):
        print(f"    {k:6s} {floor[k]:9.2e}")

    out = {"mu": MU, "N": N, "x": x.tolist(), "config": CFG, "grid_floor": floor,
           "U_newton512_every4th": {k: v.tolist() for k, v in U512.items()}, "states": {}}
    labels = CFG["checkpoints"] + ["accurate"]
    results = {}
    for kind in ("hump", "S"):
        c = 0.5 * float(np.mean(U128[kind] ** 2))
        model, entries, ckpts, ckpt_models, info = train(kind, c)

        # The ansatz allows both signs (u -> -u maps solutions to solutions). Measure against the
        # branch the fully trained run reached, and store curves on the +branch.
        acc = ckpts["accurate"]["model_U"]
        sign = -1.0 if np.max(np.abs(acc + U128[kind])) < np.max(np.abs(acc - U128[kind])) else 1.0

        run_cfg = dict(CFG, state=kind, amp_c_value=c, reference_sign=sign,
                       run_name=f"allen_cahn_pinn_accurate_w100_lbfgs/{kind}")
        logger = RunLogger(RUNS / kind, run_cfg, overwrite=True)
        nref = np.linalg.norm(U128[kind])
        for e in entries:
            U = e.pop("U")
            e["rel_l2"] = float(np.linalg.norm(U - sign * U128[kind]) / nref)
            logger.log(e)
        for step, sd in ckpt_models.items():
            torch.save(sd, logger.dir / f"ckpt_{step:06d}.pt")
        logger.final(model, summary={"final_step": info["final_step"],
                                     "final_loss_total": entries[-1]["loss_total"],
                                     "final_rel_l2": entries[-1]["rel_l2"], **info})

        curves = {}
        for lab in labels:
            U = sign * ckpts[lab]["model_U"]
            Um = sign * ckpts[lab]["model_U_mirror"]
            sym = np.max(np.abs(U + Um)) if kind == "S" else np.max(np.abs(U - Um))
            curves[lab] = {"U": U, "err_vs_N128": float(np.max(np.abs(U - U128[kind]))),
                           "err_vs_N512": float(np.max(np.abs(U - U512[kind]))),
                           "loss": ckpts[lab]["loss"], "symmetry_err": float(sym)}
        for lab in labels:
            curves[lab]["stability"] = evolve(curves[lab]["U"], kind, U128["hump"], U128["S"])
        results[kind] = (curves, info, sign)
        out["states"][kind] = {
            "reference_sign": sign, "amp_c": c, "lbfgs": info,
            "curves": {str(lab): {**{k: v for k, v in cv.items() if k != "U"}, "U": cv["U"].tolist(),
                                  "steps": lab if lab != "accurate" else info["final_step"]}
                       for lab, cv in curves.items()}}

    print("\n[2] Error vs checkpoint (curves on the + branch)")
    print(f"    {'state':5s} {'ckpt':>9s} {'err N=128':>10s} {'err N=512':>10s} {'loss':>9s} {'sym err':>9s}")
    for kind, (curves, info, sign) in results.items():
        for lab, cv in curves.items():
            print(f"    {kind:5s} {str(lab):>9s} {cv['err_vs_N128']:10.2e} {cv['err_vs_N512']:10.2e} "
                  f"{cv['loss']:9.2e} {cv['symmetry_err']:9.1e}")
        print(f"    {kind}: trained onto the {'-' if sign < 0 else '+'}{kind} branch"
              + (" (curves sign-flipped)" if sign < 0 else ""))

    print("\n[3] L-BFGS")
    print(f"    {'state':5s} {'iters':>6s} {'final step':>10s}  stop reason")
    for kind, (curves, info, sign) in results.items():
        print(f"    {kind:5s} {info['lbfgs_iterations']:6d} {info['final_step']:10d}  {info['stop_reason']}")

    print("\n[4] Stability (forward Euler, N=128, to t=40)")
    print(f"    hump curves: time until ||U - hump|| < 1e-3")
    for lab, cv in results["hump"][0].items():
        t = cv["stability"]["t_to_hump"]
        print(f"      {str(lab):>9s}  {'never' if t is None else f'{t:.3f}'}")
    print(f"    S curves: min ||U - S|| (time), then where it settles (||U -/+ hump|| < 1e-3)")
    for lab, cv in results["S"][0].items():
        s = cv["stability"]
        ts = "never" if s["t_settle"] is None else f"{s['settles_at']} at t={s['t_settle']:.3f}"
        print(f"      {str(lab):>9s}  min {s['min_dist_S']:.2e} at t={s['t_min_dist_S']:.3f}  -> {ts}")

    path = DATA / "pinn_accurate_w100_lbfgs.json"
    path.write_text(json.dumps(out, indent=1))
    print("\nwrote", path)

    # ---------------- plot ----------------
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    shown = [100, 500, 2000, "accurate"]
    colors = ["tab:red", "tab:orange", "tab:green", "tab:blue"]
    for ax, kind in zip(axes[:2], ("hump", "S")):
        curves = results[kind][0]
        ax.plot(x, U128[kind], "k-", lw=3, alpha=0.35, label="exact (N=128)")
        for lab, col in zip(shown, colors):
            name = f"step {lab}" if lab != "accurate" else "accurate"
            ax.plot(x, curves[lab]["U"], "--", color=col, lw=1.3,
                    label=f"{name} ({curves[lab]['err_vs_N128']:.1e})")
        ax.set_title(f"{kind}: guess vs exact (sup err vs N=128)")
        ax.set_xlabel("x")
        ax.legend(fontsize=7)
    axes[0].set_ylabel("u")
    ax = axes[2]
    pos = np.arange(len(labels))
    for kind, col in (("hump", "tab:blue"), ("S", "tab:red")):
        curves = results[kind][0]
        ax.semilogy(pos, [curves[l]["err_vs_N128"] for l in labels], "o-", color=col, label=f"{kind} vs N=128")
        ax.semilogy(pos, [curves[l]["err_vs_N512"] for l in labels], "s--", color=col, mfc="none",
                    label=f"{kind} vs N=512")
        ax.axhline(floor[kind], color=col, lw=0.8, ls=":", label=f"{kind} grid floor")
    ax.set_xticks(pos, [str(l) for l in labels])
    ax.set_xlabel("checkpoint (Adam step / after L-BFGS)")
    ax.set_ylabel("sup error")
    ax.set_title("error vs checkpoint")
    ax.legend(fontsize=7)
    fig.tight_layout()
    png = Path(__file__).resolve().parent / "pinn_accurate_w100_lbfgs.png"
    fig.savefig(png, dpi=120)
    print("wrote", png)


if __name__ == "__main__":
    main()
