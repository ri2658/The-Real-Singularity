"""Training loop for the Burgers' PINN.

Each history entry uses the log keys agreed for the project:
    step, phase, loss_total, loss_pde, loss_ic, loss_bc, rel_l2
(rel_l2 is None when no reference is passed).

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
"""

import math
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path

import torch

from .data import sample_points
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
    sampling: str = "uniform"        # "uniform" or "shock" (see pinn/data.py)
    shock_frac: float = 0.5          # shock sampling: fraction of n_col placed near x = 0
    shock_width: float = 0.05        # shock sampling: std of those points in x

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

    # run logging (None = keep history in memory only, write nothing)
    run_name: str = None
    runs_dir: str = "runs"
    ckpt_every: int = 500


def _log_entry(step, phase, losses, total, model, ref):
    return {
        "step": step,
        "phase": phase,
        "loss_total": float(total.item()),
        "loss_pde": float(losses["pde"].item()),
        "loss_ic": float(losses["ic"].item()),
        "loss_bc": float(losses["bc"].item()),
        "rel_l2": rel_l2_grid(model, ref) if ref is not None else None,
    }


def _print_entry(entry, t0):
    err = f"{entry['rel_l2']:.3e}" if entry["rel_l2"] is not None else "n/a"
    print(
        f"[{entry['phase']}] step {entry['step']:6d} | loss {entry['loss_total']:.3e} "
        f"(pde {entry['loss_pde']:.2e}, ic {entry['loss_ic']:.2e}, "
        f"bc {entry['loss_bc']:.2e}) | rel_l2 {err} | {time.time() - t0:.0f}s",
        flush=True,
    )


def train(cfg: TrainConfig, ref: dict = None, overwrite: bool = False):
    """Train a PINN with Adam, then optionally L-BFGS. Returns (model, history, cfg_dict)."""
    torch.manual_seed(cfg.seed)
    model = PINN(cfg.depth, cfg.width, cfg.init).to(cfg.device)
    pts = sample_points(cfg.n_ic, cfg.n_bc, cfg.n_col, seed=cfg.seed, device=cfg.device,
                        sampling=cfg.sampling, shock_frac=cfg.shock_frac,
                        shock_width=cfg.shock_width)

    cfg_dict = asdict(cfg)
    logger = None
    if cfg.run_name is not None:
        logger = RunLogger(Path(cfg.runs_dir) / cfg.run_name, cfg_dict, overwrite=overwrite)
        print(f"logging to {logger.dir}")

    history = []
    t0 = time.time()

    def record(step, phase, losses, loss, force=False):
        """Log every log_every steps (and when forced), checkpoint every ckpt_every steps."""
        if force or step % cfg.log_every == 0:
            entry = _log_entry(step, phase, losses, loss, model, ref)
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
        opt.zero_grad()
        losses = compute_losses(model, pts, cfg.nu)
        loss = total_loss(losses, cfg.weights)

        # Log before the update so step 0 is the untrained network.
        record(step, "adam", losses, loss, force=(step == cfg.adam_steps))

        if step == cfg.adam_steps:
            break
        loss.backward()
        opt.step()

    # ---------------- phase 2: L-BFGS ----------------
    if cfg.lbfgs_steps > 0:
        # max_iter=1: each .step() call is one L-BFGS iteration, so we can log
        # per iteration. The curvature history is kept in the optimizer state
        # between calls, so this is the same algorithm as one long call.
        #
        # max_eval MUST be set explicitly: PyTorch's default is max_iter * 5 // 4,
        # which is 1 here, and with a budget of one function evaluation the line
        # search never moves the parameters (the loss stays exactly constant).
        lbfgs = torch.optim.LBFGS(
            model.parameters(),
            lr=1.0,
            max_iter=1,
            max_eval=25,
            history_size=cfg.lbfgs_history,
            tolerance_grad=1e-12,
            tolerance_change=1e-15,
            line_search_fn="strong_wolfe",
        )
        last = {}

        def closure():
            lbfgs.zero_grad()
            losses = compute_losses(model, pts, cfg.nu)
            loss = total_loss(losses, cfg.weights)
            loss.backward()
            last["losses"], last["loss"] = losses, loss
            return loss

        best, since_best = float("inf"), 0
        step = cfg.adam_steps
        for k in range(1, cfg.lbfgs_steps + 1):
            step = cfg.adam_steps + k
            # .step returns the loss at the start of this iteration,
            # i.e. the loss after the previous iteration; good enough for
            # divergence / stall detection without an extra evaluation.
            value = float(lbfgs.step(closure).detach())

            if not math.isfinite(value):
                print(f"[lbfgs] step {step}: loss is {value}, stopping")
                break

            if value < best * (1 - 1e-6):
                best, since_best = value, 0
            else:
                since_best += 1
            stalled = since_best >= cfg.lbfgs_patience
            is_last = k == cfg.lbfgs_steps or stalled

            if is_last or step % cfg.log_every == 0 or (cfg.ckpt_every and step % cfg.ckpt_every == 0):
                # Fresh losses at the current parameters, only when logging.
                losses = compute_losses(model, pts, cfg.nu)
                record(step, "lbfgs", losses, total_loss(losses, cfg.weights), force=is_last)

            if stalled:
                print(f"[lbfgs] no improvement for {cfg.lbfgs_patience} steps, stopping at step {step}")
                break

    if logger is not None:
        final = history[-1]
        logger.final(model, summary={
            "final_step": final["step"],
            "final_loss_total": final["loss_total"],
            "final_rel_l2": final["rel_l2"],
            "wall_time_s": round(time.time() - t0, 1),
        })

    return model, history, cfg_dict


if __name__ == "__main__":
    cfg = TrainConfig(nu=0.01 / math.pi, adam_steps=200, print_every=50)
    train(cfg)
