"""Fully connected PINN that maps (x, t) -> u."""

import torch
import torch.nn as nn


class PINN(nn.Module):
    """MLP with `depth` hidden layers of `width` units and tanh activations.

    depth=3, width=64 reproduces the tutorial network (SimplePINN).
    depth=8, width=20 is the Raissi et al. (2019) Burgers configuration.

    init:
        "default" -- PyTorch's default Linear init (matches the tutorial)
        "xavier"  -- Xavier-normal weights, zero biases (standard for PINNs)
    """

    def __init__(self, depth: int = 3, width: int = 64, init: str = "default"):
        super().__init__()
        if depth < 1:
            raise ValueError("depth must be >= 1")

        layers = [nn.Linear(2, width), nn.Tanh()]
        for _ in range(depth - 1):
            layers += [nn.Linear(width, width), nn.Tanh()]
        layers.append(nn.Linear(width, 1))
        self.net = nn.Sequential(*layers)

        self.depth = depth
        self.width = width

        if init == "xavier":
            for m in self.net:
                if isinstance(m, nn.Linear):
                    nn.init.xavier_normal_(m.weight)
                    nn.init.zeros_(m.bias)
        elif init != "default":
            raise ValueError(f"unknown init: {init!r}")

    def forward(self, x: torch.Tensor, t: torch.Tensor) -> torch.Tensor:
        """x, t: tensors of shape (N, 1). Returns u of shape (N, 1)."""
        return self.net(torch.cat([x, t], dim=1))
