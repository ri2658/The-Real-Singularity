"""Physics-informed neural network for the viscous Burgers' equation.

    u_t + u * u_x = nu * u_xx,   x in [-1, 1],  t in [0, 1]
    u(x, 0) = -sin(pi x),        u(-1, t) = u(1, t) = 0

Modules:
    model      -- the network
    data       -- initial / boundary / collocation point sampling
    losses     -- PDE residual and the three loss terms
    reference  -- Cole-Hopf reference solution and relative L2 error
    train      -- training loop with per-step history
"""

from .model import PINN
from .data import sample_points
from .losses import compute_losses, total_loss
from .reference import (
    burgers_exact,
    burgers_exact_trapz,
    reference_path,
    make_reference,
    save_reference,
    load_reference,
    rel_l2_grid,
)
from .train import TrainConfig, train

__all__ = [
    "PINN",
    "sample_points",
    "compute_losses",
    "total_loss",
    "burgers_exact",
    "burgers_exact_trapz",
    "reference_path",
    "make_reference",
    "save_reference",
    "load_reference",
    "rel_l2_grid",
    "TrainConfig",
    "train",
]
