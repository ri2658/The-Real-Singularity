"""Training loop for the Burgers' PINN.

Each history entry uses the log keys agreed for the project:
    step, phase, loss_total, loss_pde, loss_ic, loss_bc, rel_l2
(rel_l2 is None when no reference is passed). With cfg.fresh_every > 0, entries at
multiples of fresh_every (and the last one) also carry
    loss_pde_fresh    mean squared PDE residual on the fixed set of 200,000 new points
                      (pinn/fresh.py), i.e. the same PDE term graded on points the PINN
                      never trained on
The total score on new points is then w_pde * loss_pde_fresh + w_ic * loss_ic + w_bc * loss_bc.
Every entry also carries
    evals             loss + gradient evaluations so far (one per Adam step; one per L-BFGS
                      line-search evaluation, up to 25 per L-BFGS step), to compare optimisers
                      by work done rather than by step count

If cfg.run_name is set, the run is saved to runs/<run_name>/ (see pinn/runlog.py):
config.json, history.json, periodic checkpoints and final.pt.

Two optimisation phases:
    1. Adam for `adam_steps` steps        (phase="adam")
       Robust far from the minimum, but oscillates near it.
    2. L-BFGS for up to `lbfgs_steps` steps (phase="lbfgs"), optional
       Quasi-Newton: builds a curvature estimate from recent gradients and
       uses a line search, so it converges much more precisely once Adam has
       brought the network close to a good minimum.
`step` counts optimizer steps across both phases, so it keeps increasing.

Collocation points (cfg.sampling, see pinn/data.py):
    "uniform", "shock"   fixed for the whole run. L-BFGS runs as one long phase and stops
                         after lbfgs_patience steps without improvement.
    "resample", "rad"    redrawn during training, with no prior knowledge of where the shock
                         is: uniform again ("resample") or packed where the PDE residual is
                         large ("rad", Wu et al. 2023).
                         - Adam: new points every `resample_every` steps.
                         - L-BFGS: rounds of `lbfgs_round` steps. Each round starts with new
                           points and a NEW L-BFGS optimizer, because L-BFGS keeps a curvature
                           history that assumes the loss does not change; reusing it across a
                           resample would mix curvature from two different losses. A round
                           ends early if its loss stalls for lbfgs_patience steps. The phase
                           ends when lbfgs_steps steps are used up.
"""

import math
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path

import torch

from .data import ADAPTIVE_METHODS, rad_collocation, resample_uniform, sample_points
from .fresh import fresh_points, mean_r2
from .losses import compute_losses, total_loss
from .model import PINN
from .reference import rel_l2_grid
from .runlog import RunLogger


@dataclass
class TrainConfig:
    # PDE: required on purpose, no default (avoids the 0.01 vs 0.01/pi mix-up)
    nu: float

    # network
    depth: int = 3
    width: int = 64
    init: str = "default"

    # data
    n_ic: int = 100
    n_bc: int = 100
    n_col: int = 2000
    sampling: str = "uniform"        # "uniform", "shock", "resample" or "rad" (see pinn/data.py)
    shock_frac: float = 0.5          # shock sampling: fraction of n_col placed near x = 0
    shock_width: float = 0.05        # shock sampling: std of those points in x
    resample_every: int = 250        # resample / rad: new points every this many Adam steps
    lbfgs_round: int = 1000          # resample / rad: L-BFGS steps per round (new points + new L-BFGS)
    rad_k: float = 1.0               # rad: sampling density |r|^k / mean(|r|^k) + c
    rad_c: float = 1.0
    rad_pool: int = 100_000          # rad: uniform candidate points per resample

    # optimisation
    adam_steps: int = 5000
    lr: float = 1e-3
    weights: dict = field(default_factory=lambda: {"pde": 0.1, "ic": 0.1, "bc": 0.1})

    # L-BFGS phase after Adam (0 = Adam only, same as the tutorial)
    lbfgs_steps: int = 0
    lbfgs_history: int = 50          # number of past gradients used for curvature
    lbfgs_patience: int = 200        # stop if the loss has not improved for this many steps

    # bookkeeping
    seed: int = 0
    log_every: int = 50
    print_every: int = 500
    device: str = "cpu"
    fresh_every: int = 0             # log the PDE term on 200,000 new points every this many steps (0 = off)

    # run logging (None = keep history in memory only, write nothing)
    run_name: str = None
    runs_dir: str = "runs"
    ckpt_every: int = 500


def _print_entry(entry, t0):
    err = f"{entry['rel_l2']:.3e}" if entry["rel_l2"] is not None else "n/a"
    fresh = f", new {entry['loss_pde_fresh']:.2e}" if entry.get("loss_pde_fresh") is not None else ""
    print(
        f"[{entry['phase']}] step {entry['step']:6d} | loss {entry['loss_total']:.3e} "
        f"(pde {entry['loss_pde']:.2e}{fresh}, ic {entry['loss_ic']:.2e}, "
        f"bc {entry['loss_bc']:.2e}) | rel_l2 {err} | {time.time() - t0:.0f}s",
        flush=True,
    )


def _make_lbfgs(model, cfg):
    # max_iter=1: each .step() call is one L-BFGS iteration, so we can log
    # per iteration. The curvature history is kept in the optimizer state
    # between calls, so this is the same algorithm as one long call.
    #
    # max_eval MUST be set explicitly: PyTorch's default is max_iter * 5 // 4,
    # which is 1 here, and with a budget of one function evaluation the line
    # search never moves the parameters (the loss stays exactly constant).
    return torch.optim.LBFGS(
        model.parameters(),
        lr=1.0,
        max_iter=1,
        max_eval=25,
        history_size=cfg.lbfgs_history,
        tolerance_grad=1e-12,
        tolerance_change=1e-15,
        line_search_fn="strong_wolfe",
    )


def train(cfg: TrainConfig, ref: dict = None, overwrite: bool = False):
    """Train a PINN with Adam, then optionally L-BFGS. Returns (model, history, cfg_dict)."""
    torch.manual_seed(cfg.seed)
    model = PINN(cfg.depth, cfg.width, cfg.init).to(cfg.device)
    pts = sample_points(cfg.n_ic, cfg.n_bc, cfg.n_col, seed=cfg.seed, device=cfg.device,
                        sampling=cfg.sampling, shock_frac=cfg.shock_frac,
                        shock_width=cfg.shock_width)
    adaptive = cfg.sampling in ADAPTIVE_METHODS
    # Separate generator for redrawing points, so the initial points match "uniform" exactly.
    regen = torch.Generator().manual_seed(cfg.seed + 10_000)
    fresh = fresh_points(device=cfg.device) if cfg.fresh_every else None

    cfg_dict = asdict(cfg)
    logger = None
    if cfg.run_name is not None:
        logger = RunLogger(Path(cfg.runs_dir) / cfg.run_name, cfg_dict, overwrite=overwrite)
        print(f"logging to {logger.dir}")

    history = []
    t0 = time.time()
    n_eval = [0]                     # loss + gradient evaluations so far

    def resample():
        """Replace the collocation points (resample / rad only)."""
        if cfg.sampling == "rad":
            x, t = rad_collocation(model, cfg.nu, cfg.n_col, regen, pool=cfg.rad_pool,
                                   k=cfg.rad_k, c=cfg.rad_c, device=cfg.device)
        else:
            x, t = resample_uniform(cfg.n_col, regen, cfg.device)
        pts["x_col"], pts["t_col"] = x, t

    def record(step, phase, losses, loss, force=False):
        """Log every log_every steps (and when forced), checkpoint every ckpt_every steps."""
        if force or step % cfg.log_every == 0:
            entry = {
                "step": step,
                "phase": phase,
                "loss_total": float(loss.item()),
                "loss_pde": float(losses["pde"].item()),
                "loss_ic": float(losses["ic"].item()),
                "loss_bc": float(losses["bc"].item()),
                "rel_l2": rel_l2_grid(model, ref) if ref is not None else None,
                "evals": n_eval[0],
            }
            if fresh is not None and (force or step % cfg.fresh_every == 0):
                entry["loss_pde_fresh"] = mean_r2(model, *fresh, cfg.nu)
            history.append(entry)
            if logger is not None:
                logger.log(entry)
            if cfg.print_every and (step % cfg.print_every == 0 or force):
                _print_entry(entry, t0)
        if logger is not None and cfg.ckpt_every and step % cfg.ckpt_every == 0:
            logger.checkpoint(model, step)

    # ---------------- phase 1: Adam ----------------
    opt = torch.optim.Adam(model.parameters(), lr=cfg.lr)
    for step in range(cfg.adam_steps + 1):
        if adaptive and 0 < step < cfg.adam_steps and step % cfg.resample_every == 0:
            resample()
        opt.zero_grad()
        losses = compute_losses(model, pts, cfg.nu)
        loss = total_loss(losses, cfg.weights)

        # Log before the update so step 0 is the untrained network.
        record(step, "adam", losses, loss, force=(step == cfg.adam_steps))

        if step == cfg.adam_steps:
            break
        loss.backward()
        opt.step()
        n_eval[0] += 1

    # ---------------- phase 2: L-BFGS ----------------
    # Fixed points: one round of up to lbfgs_steps. Adaptive: rounds of lbfgs_round steps,
    # each with new points and a new optimizer.
    if cfg.lbfgs_steps > 0:
        round_len = cfg.lbfgs_round if adaptive else cfg.lbfgs_steps
        step, done, stop = cfg.adam_steps, 0, False
        while done < cfg.lbfgs_steps and not stop:
            if adaptive:
                resample()
            lbfgs = _make_lbfgs(model, cfg)

            def closure():
                n_eval[0] += 1
                lbfgs.zero_grad()
                closs = total_loss(compute_losses(model, pts, cfg.nu), cfg.weights)
                closs.backward()
                return closs

            n = min(round_len, cfg.lbfgs_steps - done)
            best, since_best = float("inf"), 0
            for k in range(1, n + 1):
                step += 1
                done += 1
                # .step returns the loss at the start of this iteration,
                # i.e. the loss after the previous iteration; good enough for
                # divergence / stall detection without an extra evaluation.
                value = float(lbfgs.step(closure).detach())

                if not math.isfinite(value):
                    print(f"[lbfgs] step {step}: loss is {value}, stopping")
                    stop = True
                    break

                if value < best * (1 - 1e-6):
                    best, since_best = value, 0
                else:
                    since_best += 1
                stalled = since_best >= cfg.lbfgs_patience
                if stalled and not adaptive:
                    stop = True
                is_last = done == cfg.lbfgs_steps or stop

                if is_last or step % cfg.log_every == 0 or (cfg.ckpt_every and step % cfg.ckpt_every == 0):
                    # Fresh losses at the current parameters, only when logging.
                    losses = compute_losses(model, pts, cfg.nu)
                    record(step, "lbfgs", losses, total_loss(losses, cfg.weights), force=is_last)

                if stalled:
                    print(f"[lbfgs] no improvement for {cfg.lbfgs_patience} steps, "
                          f"{'stopping' if stop else 'ending this round'} at step {step}")
                    break

    if logger is not None:
        final = history[-1]
        logger.final(model, summary={
            "final_step": final["step"],
            "final_loss_total": final["loss_total"],
            "final_rel_l2": final["rel_l2"],
            "final_loss_pde_fresh": final.get("loss_pde_fresh"),
            "wall_time_s": round(time.time() - t0, 1),
        })

    return model, history, cfg_dict


if __name__ == "__main__":
    cfg = TrainConfig(nu=0.01 / math.pi, adam_steps=200, print_every=50)
    train(cfg)
