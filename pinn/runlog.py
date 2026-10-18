"""Run logging: one folder per training run.

    runs/<run_name>/
        config.json            training settings (nu, network, steps, seed, ...)
        history.json           list of log entries, rewritten after every entry
        ckpt_000000.pt ...     model weights every `ckpt_every` steps
        final.pt               model weights at the end of training

history.json entries:
    {"step", "phase", "loss_total", "loss_pde", "loss_ic", "loss_bc", "rel_l2"}
    phase is "adam" (later also "lbfgs"); rel_l2 is null if no reference was given.
    `step` counts optimizer steps across all phases, so it keeps increasing.

Files are written atomically (temp file + rename), so history.json can be
read while a run is still going.

Reading a run (e.g. for plots or for computing your own error metric):

    from pinn.runlog import load_run, load_checkpoint
    config, history = load_run("runs/my_run")
    model = load_checkpoint("runs/my_run")             # final weights
    model = load_checkpoint("runs/my_run", step=1000)  # weights at step 1000
"""

import json
import os
from pathlib import Path

import torch

from .model import PINN


def _atomic_write_json(path: Path, obj) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=1)
    os.replace(tmp, path)


class RunLogger:
    def __init__(self, run_dir, config: dict, overwrite: bool = False):
        self.dir = Path(run_dir)
        if self.dir.exists() and any(self.dir.iterdir()) and not overwrite:
            raise FileExistsError(
                f"{self.dir} already exists; pick a new run_name or pass overwrite=True"
            )
        self.dir.mkdir(parents=True, exist_ok=True)
        self.history = []
        _atomic_write_json(self.dir / "config.json", config)

    def log(self, entry: dict) -> None:
        self.history.append(entry)
        _atomic_write_json(self.dir / "history.json", self.history)

    def checkpoint(self, model, step: int) -> Path:
        path = self.dir / f"ckpt_{step:06d}.pt"
        torch.save(model.state_dict(), path)
        return path

    def final(self, model, summary: dict = None) -> None:
        torch.save(model.state_dict(), self.dir / "final.pt")
        if summary is not None:
            _atomic_write_json(self.dir / "summary.json", summary)


def load_run(run_dir):
    """Return (config, history) for a run folder."""
    run_dir = Path(run_dir)
    with open(run_dir / "config.json") as f:
        config = json.load(f)
    hist_path = run_dir / "history.json"
    history = json.load(open(hist_path)) if hist_path.exists() else []
    return config, history


def list_checkpoints(run_dir):
    """Steps that have a saved checkpoint, sorted."""
    return sorted(int(p.stem.split("_")[1]) for p in Path(run_dir).glob("ckpt_*.pt"))


def load_checkpoint(run_dir, step: int = None, device: str = "cpu"):
    """Rebuild the PINN from config.json and load weights.

    step=None loads final.pt (or the last checkpoint if the run did not finish).
    """
    run_dir = Path(run_dir)
    config, _ = load_run(run_dir)
    model = PINN(config["depth"], config["width"], config.get("init", "default"))

    if step is None:
        path = run_dir / "final.pt"
        if not path.exists():
            steps = list_checkpoints(run_dir)
            if not steps:
                raise FileNotFoundError(f"no checkpoints in {run_dir}")
            path = run_dir / f"ckpt_{steps[-1]:06d}.pt"
    else:
        path = run_dir / f"ckpt_{step:06d}.pt"

    model.load_state_dict(torch.load(path, map_location=device))
    model.to(device).eval()
    return model
