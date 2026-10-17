"""Train one PINN and save everything to runs/<name>/.

Examples (run from the repo root):
    python scripts/run.py --name sample_adam500 --adam-steps 500
    python scripts/run.py --name baseline_s0 --seed 0
    python scripts/run.py --name deep_8x20 --depth 8 --width 20 --init xavier --n-col 10000

The reference solution (nu = 0.01/pi) is loaded so rel_l2 is logged at every
log step. For other nu values rel_l2 is not logged (reference not trustworthy).
"""

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pinn import TrainConfig, train, make_reference, load_reference, save_reference
from pinn.reference import DEFAULT_REF_PATH, NU_BENCHMARK


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--name", required=True, help="run folder name under runs/")
    p.add_argument("--nu-pi", type=float, default=0.01,
                   help="nu in units of 1/pi (default 0.01 -> nu = 0.01/pi)")
    p.add_argument("--depth", type=int, default=3)
    p.add_argument("--width", type=int, default=64)
    p.add_argument("--init", default="default", choices=["default", "xavier"])
    p.add_argument("--n-col", type=int, default=2000)
    p.add_argument("--adam-steps", type=int, default=5000)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--log-every", type=int, default=50)
    p.add_argument("--ckpt-every", type=int, default=500)
    p.add_argument("--overwrite", action="store_true")
    return p.parse_args()


def main():
    a = parse_args()
    nu = a.nu_pi / math.pi

    ref = None
    if math.isclose(nu, NU_BENCHMARK):
        if not DEFAULT_REF_PATH.exists():
            save_reference(make_reference(), DEFAULT_REF_PATH)
        ref = load_reference(DEFAULT_REF_PATH)

    cfg = TrainConfig(
        nu=nu, depth=a.depth, width=a.width, init=a.init, n_col=a.n_col,
        adam_steps=a.adam_steps, lr=a.lr, seed=a.seed,
        log_every=a.log_every, ckpt_every=a.ckpt_every, run_name=a.name,
    )
    _, history, _ = train(cfg, ref=ref, overwrite=a.overwrite)

    last = history[-1]
    err = f"{last['rel_l2']:.4e}" if last["rel_l2"] is not None else "n/a"
    print(f"\ndone: runs/{a.name}  final loss {last['loss_total']:.3e}  rel_l2 {err}")


if __name__ == "__main__":
    main()
