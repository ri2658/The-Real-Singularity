"""Training point sampling for the Burgers' benchmark.

All points are returned in one dict so the loss functions take them as an
argument instead of reading global variables.
"""

import math

import torch


def initial_condition(x: torch.Tensor) -> torch.Tensor:
    """u(x, 0) = -sin(pi x)."""
    return -torch.sin(math.pi * x)


SAMPLING_METHODS = ("uniform", "shock")


def sample_points(
    n_ic: int = 100,
    n_bc: int = 100,
    n_col: int = 2000,
    seed: int = 0,
    device: str = "cpu",
    sampling: str = "uniform",
    shock_frac: float = 0.5,
    shock_width: float = 0.05,
) -> dict:
    """Sample initial, boundary and interior collocation points.

    Domain: x in [-1, 1], t in [0, 1].

    sampling:
        "uniform"  all n_col collocation points uniform over the domain (default;
                   identical to the week-3 runs).
        "shock"    same total n_col, but a fraction `shock_frac` of them is placed
                   near the shock at x = 0: x ~ Normal(0, shock_width) (kept inside
                   [-1, 1]), t uniform in [0, 1]. The rest stay uniform.
                   Uses prior knowledge of where the shock forms (x = 0 for this
                   initial condition), not the residual.

    Returns a dict of (N, 1) float32 tensors:
        x_ic, t_ic, u_ic      initial condition: x evenly spaced, t = 0
        t_bc                  boundary times, sampled uniformly
                              (used for both x = -1 and x = 1, target u = 0)
        x_col, t_col          interior points where the PDE residual is enforced
    """
    if sampling not in SAMPLING_METHODS:
        raise ValueError(f"sampling must be one of {SAMPLING_METHODS}, got {sampling!r}")

    gen = torch.Generator().manual_seed(seed)

    x_ic = torch.linspace(-1.0, 1.0, n_ic).view(-1, 1)
    t_ic = torch.zeros_like(x_ic)
    u_ic = initial_condition(x_ic)

    t_bc = torch.rand(n_bc, 1, generator=gen)

    if sampling == "uniform":
        x_col = torch.rand(n_col, 1, generator=gen) * 2.0 - 1.0
        t_col = torch.rand(n_col, 1, generator=gen)
    else:
        if not 0.0 <= shock_frac <= 1.0:
            raise ValueError("shock_frac must be in [0, 1]")
        n_shock = int(round(shock_frac * n_col))
        n_unif = n_col - n_shock

        x_unif = torch.rand(n_unif, 1, generator=gen) * 2.0 - 1.0
        t_unif = torch.rand(n_unif, 1, generator=gen)

        # Normal(0, shock_width) in x, redrawn until inside [-1, 1].
        x_shock = torch.randn(n_shock, 1, generator=gen) * shock_width
        outside = x_shock.abs() > 1.0
        while outside.any():
            x_shock[outside] = torch.randn(int(outside.sum()), generator=gen) * shock_width
            outside = x_shock.abs() > 1.0
        t_shock = torch.rand(n_shock, 1, generator=gen)

        x_col = torch.cat([x_unif, x_shock])
        t_col = torch.cat([t_unif, t_shock])

    pts = {
        "x_ic": x_ic,
        "t_ic": t_ic,
        "u_ic": u_ic,
        "t_bc": t_bc,
        "x_col": x_col,
        "t_col": t_col,
    }
    return {k: v.to(device) for k, v in pts.items()}
