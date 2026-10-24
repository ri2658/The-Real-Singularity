"""Train one PINN and save everything to runs/<name>/.

Examples (run from the repo root):
    python scripts/run.py --name sample_adam500 --adam-steps 500
    python scripts/run.py --name baseline_s0 --seed 0
    python scripts/run.py --name deep_8x20 --depth 8 --width 20 --init xavier --n-col 10000
    python scripts/run.py --name lbfgs_8x20 --depth 8 --width 20 --init xavier --n-col 10000 \
        --adam-steps 2000 --lbfgs-steps 10000

The reference solution for the chosen nu (data/reference/burgers_nu<nu_pi>pi.npz)
is loaded, or generated if missing, so rel_l2 is logged at every log step.
Week-4 nu sweep example:
    python scripts/run.py --name nu0.001_s0 --nu-pi 0.001 --depth 8 --width 20 --init xavier \
        --n-col 10000 --adam-steps 2000 --lbfgs-steps 15000
"""

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pinn import TrainConfig, train, make_reference, load_reference, save_reference
from pinn.reference import reference_path


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
    p.add_argument("--lbfgs-steps", type=int, default=0,
                   help="max L-BFGS iterations after Adam (0 = Adam only)")
    p.add_argument("--lbfgs-patience", type=int, default=200)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--log-every", type=int, default=50)
    p.add_argument("--ckpt-every", type=int, default=500)
    p.add_argument("--overwrite", action="store_true")
    return p.parse_args()


def main():
    a = parse_args()
    nu = a.nu_pi / math.pi

    # Reference for this nu: data/reference/burgers_nu<nu_pi>pi.npz, generated if missing.
    ref_path = reference_path(a.nu_pi)
    if not ref_path.exists():
        print(f"generating {ref_path} ...")
        save_reference(make_reference(nu=nu), ref_path)
    ref = load_reference(ref_path)

    cfg = TrainConfig(
        nu=nu, depth=a.depth, width=a.width, init=a.init, n_col=a.n_col,
        adam_steps=a.adam_steps, lr=a.lr, seed=a.seed,
        lbfgs_steps=a.lbfgs_steps, lbfgs_patience=a.lbfgs_patience,
        log_every=a.log_every, ckpt_every=a.ckpt_every, run_name=a.name,
    )
    _, history, _ = train(cfg, ref=ref, overwrite=a.overwrite)

    last = history[-1]
    err = f"{last['rel_l2']:.4e}" if last["rel_l2"] is not None else "n/a"
    print(f"\ndone: runs/{a.name}  final loss {last['loss_total']:.3e}  rel_l2 {err}")


if __name__ == "__main__":
    main()
