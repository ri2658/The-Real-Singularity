"""Train one PINN and save everything to runs/<name>/.

Examples (run from the repo root):
    python scripts/run.py --name sample_adam500 --adam-steps 500
    python scripts/run.py --name baseline_s0 --seed 0
    python scripts/run.py --name deep_8x20 --depth 8 --width 20 --init xavier --n-col 10000
    python scripts/run.py --name lbfgs_8x20 --depth 8 --width 20 --init xavier --n-col 10000 \
        --adam-steps 2000 --lbfgs-steps 10000

The reference solution for the chosen nu (data/reference/burgers_nu<nu_pi>pi.npz)
is loaded, or generated if missing, so rel_l2 is logged at every log step.
Week-4 nu sweep examples (uniform vs. shock-focused collocation):
    python scripts/run.py --name nu0.001_vanilla_s0 --nu-pi 0.001 --depth 8 --width 20 --init xavier \
        --n-col 10000 --adam-steps 2000 --lbfgs-steps 15000 --lbfgs-patience 1000
    python scripts/run.py --name nu0.001_shock_s0 --nu-pi 0.001 --sampling shock --depth 8 --width 20 \
        --init xavier --n-col 10000 --adam-steps 2000 --lbfgs-steps 15000 --lbfgs-patience 1000

Week-5 runs: check points that move to where the equation is broken (no prior knowledge of the
shock), and an Adam-only control. --device cuda needs the CUDA build of torch (.venv-gpu, see
pinn/README.md); the run name ends in the device it trained on:
    .venv-gpu/Scripts/python scripts/run.py --name nu0.003_rad_s0_gpu --nu-pi 0.003 --sampling rad \
        --depth 8 --width 20 --init xavier --n-col 10000 --adam-steps 2000 --lbfgs-steps 15000 \
        --lbfgs-patience 1000 --seed 0 --device cuda
    python scripts/run.py --name nu0.003_adamonly_s0_cpu --nu-pi 0.003 --depth 8 --width 20 \
        --init xavier --n-col 10000 --adam-steps 50000 --lbfgs-steps 0 --seed 0
Every run logs the PDE term on 200,000 new points every 500 steps (--fresh-every, pinn/fresh.py).
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
    p.add_argument("--sampling", default="uniform", choices=["uniform", "shock", "resample", "rad"],
                   help="collocation points: uniform (fixed), shock (half near x = 0, fixed), "
                        "resample (uniform, redrawn) or rad (redrawn where the residual is large)")
    p.add_argument("--resample-every", type=int, default=250,
                   help="resample / rad: new points every this many Adam steps")
    p.add_argument("--lbfgs-round", type=int, default=1000,
                   help="resample / rad: L-BFGS steps per round; each round starts with new points "
                        "and a new L-BFGS optimizer")
    p.add_argument("--rad-k", type=float, default=1.0, help="rad: density |r|^k / mean(|r|^k) + c")
    p.add_argument("--rad-c", type=float, default=1.0)
    p.add_argument("--rad-pool", type=int, default=100_000, help="rad: uniform candidates per resample")
    p.add_argument("--shock-frac", type=float, default=0.5,
                   help="shock sampling: fraction of collocation points placed near x = 0")
    p.add_argument("--shock-width", type=float, default=0.05,
                   help="shock sampling: std in x of the points near the shock")
    p.add_argument("--adam-steps", type=int, default=5000)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--lbfgs-steps", type=int, default=0,
                   help="max L-BFGS iterations after Adam (0 = Adam only)")
    p.add_argument("--lbfgs-patience", type=int, default=200)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--log-every", type=int, default=50)
    p.add_argument("--ckpt-every", type=int, default=500)
    p.add_argument("--fresh-every", type=int, default=500,
                   help="log the PDE term on 200,000 new points every this many steps (0 = off)")
    p.add_argument("--device", default="cpu",
                   help="cpu, cuda or cuda:N. Training stays float32 (GeForce cards are slow at float64)")
    p.add_argument("--overwrite", action="store_true")
    return p.parse_args()


def main():
    a = parse_args()
    nu = a.nu_pi / math.pi
    if a.device.startswith("cuda"):
        import torch
        if not torch.cuda.is_available():
            raise SystemExit(f"--device {a.device}: this torch ({torch.__version__}) has no CUDA; "
                             "use the CUDA build (.venv-gpu) or --device cpu")
        print(f"device: {torch.cuda.get_device_name(a.device)}")

    # Reference for this nu: data/reference/burgers_nu<nu_pi>pi.npz, generated if missing.
    ref_path = reference_path(a.nu_pi)
    if not ref_path.exists():
        print(f"generating {ref_path} ...")
        save_reference(make_reference(nu=nu), ref_path)
    ref = load_reference(ref_path)

    cfg = TrainConfig(
        nu=nu, depth=a.depth, width=a.width, init=a.init, n_col=a.n_col,
        sampling=a.sampling, shock_frac=a.shock_frac, shock_width=a.shock_width,
        adam_steps=a.adam_steps, lr=a.lr, seed=a.seed,
        lbfgs_steps=a.lbfgs_steps, lbfgs_patience=a.lbfgs_patience,
        resample_every=a.resample_every, lbfgs_round=a.lbfgs_round,
        rad_k=a.rad_k, rad_c=a.rad_c, rad_pool=a.rad_pool,
        log_every=a.log_every, ckpt_every=a.ckpt_every, fresh_every=a.fresh_every,
        device=a.device, run_name=a.name,
    )
    _, history, _ = train(cfg, ref=ref, overwrite=a.overwrite)

    last = history[-1]
    err = f"{last['rel_l2']:.4e}" if last["rel_l2"] is not None else "n/a"
    print(f"\ndone: runs/{a.name}  final loss {last['loss_total']:.3e}  rel_l2 {err}")


if __name__ == "__main__":
    main()
