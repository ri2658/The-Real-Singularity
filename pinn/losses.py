"""Loss terms for the Burgers' PINN.

The three terms are returned separately so training can log each one:
    pde  -- mean squared PDE residual on the collocation points
    ic   -- MSE against u(x, 0) = -sin(pi x)
    bc   -- MSE against u(-1, t) = u(1, t) = 0 (left + right)
"""

import torch


def _grad(out: torch.Tensor, inp: torch.Tensor) -> torch.Tensor:
    return torch.autograd.grad(
        out, inp, grad_outputs=torch.ones_like(out), create_graph=True
    )[0]


def pde_residual(model, x: torch.Tensor, t: torch.Tensor, nu: float) -> torch.Tensor:
    """r = u_t + u * u_x - nu * u_xx, evaluated at (x, t). Shape (N, 1).

    Inputs are cloned so the caller's tensors are not modified in place.
    """
    x = x.detach().clone().requires_grad_(True)
    t = t.detach().clone().requires_grad_(True)

    u = model(x, t)
    u_x = _grad(u, x)
    u_t = _grad(u, t)
    u_xx = _grad(u_x, x)
    return u_t + u * u_x - nu * u_xx


def loss_pde(model, pts: dict, nu: float) -> torch.Tensor:
    r = pde_residual(model, pts["x_col"], pts["t_col"], nu)
    return torch.mean(r ** 2)


def loss_ic(model, pts: dict) -> torch.Tensor:
    u_pred = model(pts["x_ic"], pts["t_ic"])
    return torch.mean((u_pred - pts["u_ic"]) ** 2)


def loss_bc(model, pts: dict) -> torch.Tensor:
    t_bc = pts["t_bc"]
    x_left = -torch.ones_like(t_bc)
    x_right = torch.ones_like(t_bc)
    u_left = model(x_left, t_bc)
    u_right = model(x_right, t_bc)
    # Same convention as the tutorial: sum of the left and right MSEs.
    return torch.mean(u_left ** 2) + torch.mean(u_right ** 2)


def compute_losses(model, pts: dict, nu: float) -> dict:
    """Return {"pde": ..., "ic": ..., "bc": ...} as scalar tensors."""
    return {
        "pde": loss_pde(model, pts, nu),
        "ic": loss_ic(model, pts),
        "bc": loss_bc(model, pts),
    }


def total_loss(losses: dict, weights: dict) -> torch.Tensor:
    """Weighted sum of the loss terms.

    The tutorial used total = 0.1 * pde + 0.1 * (ic + bc), i.e.
    weights = {"pde": 0.1, "ic": 0.1, "bc": 0.1}.
    """
    return sum(weights[k] * losses[k] for k in ("pde", "ic", "bc"))
