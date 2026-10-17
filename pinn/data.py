"""Training point sampling for the Burgers' benchmark.

All points are returned in one dict so the loss functions take them as an
argument instead of reading global variables.
"""

import math

import torch


def initial_condition(x: torch.Tensor) -> torch.Tensor:
    """u(x, 0) = -sin(pi x)."""
    return -torch.sin(math.pi * x)


def sample_points(
    n_ic: int = 100,
    n_bc: int = 100,
    n_col: int = 2000,
    seed: int = 0,
    device: str = "cpu",
) -> dict:
    """Sample initial, boundary and interior collocation points.

    Domain: x in [-1, 1], t in [0, 1].

    Returns a dict of (N, 1) float32 tensors:
        x_ic, t_ic, u_ic      initial condition: x evenly spaced, t = 0
        t_bc                  boundary times, sampled uniformly
                              (used for both x = -1 and x = 1, target u = 0)
        x_col, t_col          interior points where the PDE residual is enforced
    """
    gen = torch.Generator().manual_seed(seed)

    x_ic = torch.linspace(-1.0, 1.0, n_ic).view(-1, 1)
    t_ic = torch.zeros_like(x_ic)
    u_ic = initial_condition(x_ic)

    t_bc = torch.rand(n_bc, 1, generator=gen)

    x_col = torch.rand(n_col, 1, generator=gen) * 2.0 - 1.0
    t_col = torch.rand(n_col, 1, generator=gen)

    pts = {
        "x_ic": x_ic,
        "t_ic": t_ic,
        "u_ic": u_ic,
        "t_bc": t_bc,
        "x_col": x_col,
        "t_col": t_col,
    }
    return {k: v.to(device) for k, v in pts.items()}
