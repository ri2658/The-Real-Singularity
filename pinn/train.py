"""Training loop for the Burgers' PINN.

Each history entry uses the log keys agreed for the project:
    step, loss_total, loss_pde, loss_ic, loss_bc, rel_l2
(rel_l2 is None when no reference is passed).

Saturday's work plugs in here: L-BFGS after Adam, checkpoints, and
writing the history to a JSON file.
"""

import math
import time
from dataclasses import dataclass, field, asdict

import torch

from .data import sample_points
from .losses import compute_losses, total_loss
from .model import PINN
from .reference import rel_l2_grid


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


def _log_entry(step, losses, total, model, ref):
    return {
        "step": step,
        "loss_total": float(total.item()),
        "loss_pde": float(losses["pde"].item()),
        "loss_ic": float(losses["ic"].item()),
        "loss_bc": float(losses["bc"].item()),
        "rel_l2": rel_l2_grid(model, ref) if ref is not None else None,
    }


def train(cfg: TrainConfig, ref: dict = None):
    """Train a PINN with Adam. Returns (model, history, cfg_dict)."""
    torch.manual_seed(cfg.seed)
    model = PINN(cfg.depth, cfg.width, cfg.init).to(cfg.device)
    pts = sample_points(cfg.n_ic, cfg.n_bc, cfg.n_col, seed=cfg.seed, device=cfg.device)
    opt = torch.optim.Adam(model.parameters(), lr=cfg.lr)

    history = []
    t0 = time.time()
    for step in range(cfg.adam_steps + 1):
        opt.zero_grad()
        losses = compute_losses(model, pts, cfg.nu)
        loss = total_loss(losses, cfg.weights)

        # Log before the update so step 0 is the untrained network.
        if step % cfg.log_every == 0 or step == cfg.adam_steps:
            entry = _log_entry(step, losses, loss, model, ref)
            history.append(entry)
            if cfg.print_every and step % cfg.print_every == 0:
                err = f"{entry['rel_l2']:.3e}" if entry["rel_l2"] is not None else "n/a"
                print(
                    f"step {step:6d} | loss {entry['loss_total']:.3e} "
                    f"(pde {entry['loss_pde']:.2e}, ic {entry['loss_ic']:.2e}, "
                    f"bc {entry['loss_bc']:.2e}) | rel_l2 {err} | {time.time() - t0:.0f}s"
                )

        if step == cfg.adam_steps:
            break
        loss.backward()
        opt.step()

    return model, history, asdict(cfg)


if __name__ == "__main__":
    cfg = TrainConfig(nu=0.01 / math.pi, adam_steps=200, print_every=50)
    train(cfg)
