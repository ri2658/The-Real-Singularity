# Data

Everything the website and the analysis scripts read. `scripts/build_site.py` copies the folders the site needs
into `site/data/`.

| Folder | What it holds | Made by |
| --- | --- | --- |
| `reference/` | Exact Burgers solutions (Cole–Hopf) at $\nu = 0.01/\pi, 0.003/\pi, 0.001/\pi$, as `.npz` | `pinn/reference.py` |
| `reference_json/` | The same references for the browser (`ref_*.json`), plus the Python finite-volume check (`pycheck_*.json`) | `Finite volume solver/Export_json.py` |
| `viscosity/` | PINN predictions at the three viscosities, uniform and shock-focused training points | `scripts/export_viscosity.py` |
| `race_pinn/` | One trained PINN per viscosity, as ONNX, for the race page | `scripts/export_race_onnx.py` |
| `loss_truth/` | Training loss and true error over training, 20 runs | `scripts/export_loss_truth.py` |
| `allen_cahn/` | The five exact Allen–Cahn resting states (`equilibria.json`, Newton's method), the PINN guesses for them, the forward-Euler check, and the hilltop-escape experiment | Michelle's Newton / PINN code; `allen_cahn/js/hilltop_experiment.js` |
