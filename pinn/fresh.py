"""The score on new points: a check that needs no exact answer.

A PINN is trained on a fixed (or periodically redrawn) set of collocation points, so its
training loss can overfit them, like any training score. Re-grading the same PINN on
points it never trained on catches that, the same way a validation set does.

    FRESH_N = 200,000 points, x ~ U[-1, 1], t ~ U[0, 1], drawn once as a single (N, 2)
    tensor from torch.Generator().manual_seed(FRESH_SEED). The same set is used for every
    run, during training (pinn/train.py, cfg.fresh_every) and in the export
    (scripts/export_loss_truth.py), so the two give the same numbers.

Only the PDE term changes: the new-point score is
    w_pde * mean_r2(new points) + w_ic * loss_ic + w_bc * loss_bc
because the initial / boundary points are the same anyway.
"""

import torch

from .losses import pde_residual

FRESH_N = 200_000
FRESH_SEED = 12345
BATCH = 20_000


def fresh_points(seed: int = FRESH_SEED, n: int = FRESH_N, device="cpu"):
    """(x, t), each (n, 1) float32, spread evenly at random over x in [-1, 1], t in [0, 1]."""
    xt = torch.rand(n, 2, generator=torch.Generator().manual_seed(seed))
    return (xt[:, :1] * 2.0 - 1.0).to(device), xt[:, 1:].to(device)


def mean_r2(model, x: torch.Tensor, t: torch.Tensor, nu: float, batch: int = BATCH) -> float:
    """Mean squared PDE residual over (x, t), evaluated in batches.

    The residual needs autograd, so this cannot run under torch.no_grad(); each batch's
    graph is dropped as soon as its sum is taken. Sums are float32 per batch and float64
    across batches.
    """
    total = 0.0
    for i in range(0, len(x), batch):
        r = pde_residual(model, x[i:i + batch], t[i:i + batch], nu)
        total += float(r.detach().pow(2).sum())
    return total / len(x)
