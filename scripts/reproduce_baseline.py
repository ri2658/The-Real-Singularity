"""C3: check that the refactored pinn/ package reproduces the tutorial baseline.

Tutorial setup: 3 x 64 tanh MLP, Adam lr 1e-3, 5000 steps, 2000 collocation points,
weights 0.1 / 0.1 / 0.1, nu = 0.01/pi.
Michelle's notebook reported a full-grid relative L2 of ~0.067 for this setup.
Different random seeds give somewhat different numbers, so expect the same
order of magnitude (a few 1e-2), not an exact match.

Run from the repo root:
    python scripts/reproduce_baseline.py
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pinn import TrainConfig, train, make_reference, load_reference, save_reference, rel_l2_grid
from pinn.reference import DEFAULT_REF_PATH


def main():
    if DEFAULT_REF_PATH.exists():
        ref = load_reference(DEFAULT_REF_PATH)
    else:
        ref = make_reference()
        save_reference(ref, DEFAULT_REF_PATH)
        print(f"generated {DEFAULT_REF_PATH}")

    cfg = TrainConfig(nu=0.01 / math.pi)  # all other fields = tutorial defaults
    model, history, _ = train(cfg, ref=ref)

    final = rel_l2_grid(model, ref)
    print(f"\nfinal relative L2 (full grid): {final:.4f}")
    print("tutorial baseline (Michelle):   0.0670")


if __name__ == "__main__":
    main()
