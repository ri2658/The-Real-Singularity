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

## Known limitations

- `burgers_exact` is only trustworthy at nu = 0.01/pi. Measured error: ~1e-2 at
  nu = 0.003/pi (t = 1) and ~0.3 at nu = 0.001/pi (t = 1). `make_reference` warns below 0.01/pi.
- Baseline (3 x 64, Adam 5000 steps) is unconverged and seed-sensitive:
  full-grid rel L2 ranged 0.09–0.27 over seeds 0–4 (Michelle's run: 0.067).
