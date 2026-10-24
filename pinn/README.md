# pinn — Burgers' PINN package

Refactor of the tutorial notebooks into importable modules (week 3, task C1).

| File | Contents |
|---|---|
| `model.py` | `PINN(depth, width, init)` — tanh MLP, (x, t) -> u |
| `data.py` | `sample_points(...)` — IC / BC / collocation points, seeded |
| `losses.py` | `compute_losses(model, pts, nu)` -> `{"pde", "ic", "bc"}`; `total_loss(losses, weights)` |
| `reference.py` | `burgers_exact`, `make_reference`, `save_reference`, `load_reference`, `rel_l2_grid` |
| `train.py` | `TrainConfig`, `train(cfg, ref)` -> `(model, history, cfg_dict)` |
| `runlog.py` | `RunLogger`, `load_run`, `load_checkpoint`, `list_checkpoints` |

## Run logging

Set `run_name` (or use `scripts/run.py --name ...`) and every run is saved to `runs/<name>/`:

```
config.json        settings used (nu, depth, width, steps, seed, ...)
history.json       every log_every steps: step, phase, loss_total, loss_pde, loss_ic, loss_bc, rel_l2
ckpt_000500.pt     model weights every ckpt_every steps
final.pt           final weights
summary.json       final loss, final rel_l2, wall time
```

```bash
python scripts/run.py --name sample_adam500 --adam-steps 500
```

```python
from pinn.runlog import load_run, load_checkpoint
config, history = load_run("runs/sample_adam500")
steps = [h["step"] for h in history]; loss = [h["loss_total"] for h in history]
model = load_checkpoint("runs/sample_adam500", step=300)  # or step=None for final
```

history.json is rewritten after every entry, so it can be read while a run is in progress.

## Quick start (run from the repo root)

```bash
python -m pinn.reference              # writes data/reference/burgers_nu0.01pi.npz
python scripts/reproduce_baseline.py  # trains the tutorial setup, prints full-grid rel L2
```

```python
import math
from pinn import TrainConfig, train, load_reference

ref = load_reference()
model, history, cfg = train(TrainConfig(nu=0.01 / math.pi), ref=ref)
history[-1]  # {'step', 'loss_total', 'loss_pde', 'loss_ic', 'loss_bc', 'rel_l2'}
```

## Conventions

- `nu` has no default anywhere — always pass it explicitly (`0.01 / math.pi` for the benchmark).
- Official error metric: `rel_l2_grid` = ||u_pred - u_ref|| / ||u_ref|| over the full
  256 x 100 reference grid (x in [-1, 1], t in [0.01, 1]).
- History keys match the agreed JSON log format.

## Reference solutions

`data/reference/burgers_nu{0.01,0.003,0.001}pi.npz` (256 x 100 grid), generated with
`burgers_exact_trapz` (`python -m pinn.reference`). Validated against an independent
finite-difference PDE solve (agreement <= 2e-5) at all three nu.
`scripts/run.py --nu-pi <value>` loads the matching file automatically.

The original Gauss-Hermite `burgers_exact` is exact at nu = 0.01/pi and 0.003/pi but
off by 1.7e-2 (full grid) at nu = 0.001/pi, so it is no longer the default.

## Known limitations

- Training is seed-sensitive. Adam 2000 + L-BFGS (8 x 20, xavier, 10k points, nu = 0.01/pi),
  seeds 0-4 (runs/p1000_8x20_s*): full-grid rel L2 5.5e-4 / 5.7e-4 / 9.8e-4 / 1.3e-3 / 1.4e-3,
  median 9.8e-4, 3 of 5 below 1e-3. Report results over several seeds.
- L-BFGS stalls at loss ~5e-7 to 1e-6 in float32; raising lbfgs_patience from 200 to 1000
  did not change the final error, so further gains need other changes (e.g. float64,
  more or adaptive collocation points).
