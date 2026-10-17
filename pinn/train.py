"""Training loop for the Burgers' PINN.

Each history entry uses the log keys agreed for the project:
    step, phase, loss_total, loss_pde, loss_ic, loss_bc, rel_l2
(rel_l2 is None when no reference is passed).

If cfg.run_name is set, the run is saved to runs/<run_name>/ (see pinn/runlog.py):
config.json, history.json, periodic checkpoints and final.pt.

Saturday's remaining work plugs in here: an L-BFGS phase after Adam
(log its entries with phase="lbfgs" and keep counting `step`).
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

    # optimisation
    adam_steps: int = 5000
    lr: float = 1e-3
    weights: dict = field(default_factory=lambda: {"pde": 0.1, "ic": 0.1, "bc": 0.1})

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
    """Train a PINN with Adam. Returns (model, history, cfg_dict)."""
    torch.manual_seed(cfg.seed)
    model = PINN(cfg.depth, cfg.width, cfg.init).to(cfg.device)
    pts = sample_points(cfg.n_ic, cfg.n_bc, cfg.n_col, seed=cfg.seed, device=cfg.device)
    opt = torch.optim.Adam(model.parameters(), lr=cfg.lr)

    cfg_dict = asdict(cfg)
    logger = None
    if cfg.run_name is not None:
        logger = RunLogger(Path(cfg.runs_dir) / cfg.run_name, cfg_dict, overwrite=overwrite)
        print(f"logging to {logger.dir}")

    history = []
    t0 = time.time()
    for step in range(cfg.adam_steps + 1):
        opt.zero_grad()
        losses = compute_losses(model, pts, cfg.nu)
        loss = total_loss(losses, cfg.weights)

        # Log before the update so step 0 is the untrained network.
        if step % cfg.log_every == 0 or step == cfg.adam_steps:
            entry = _log_entry(step, "adam", losses, loss, model, ref)
            history.append(entry)
            if logger is not None:
                logger.log(entry)
            if cfg.print_every and step % cfg.print_every == 0:
                _print_entry(entry, t0)

        if logger is not None and cfg.ckpt_every and step % cfg.ckpt_every == 0:
            logger.checkpoint(model, step)

        if step == cfg.adam_steps:
            break
        loss.backward()
        opt.step()

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
