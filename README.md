# The Real Singularity

A website that explains how a physics-informed neural network (PINN) works, using the viscous Burgers' equation as the running example:

$$
\frac{\partial u}{\partial t} + u \frac{\partial u}{\partial x} = \nu \frac{\partial^2 u}{\partial x^2}
$$

## Structure

- `pinn/`: the Burgers' PINN package (model, sampling, losses, exact reference, training, run logging). See [`pinn/README.md`](./pinn/README.md).
- `scripts/`: training runs, ONNX and data exports, and the site build and publish scripts
- `runs/`: saved training runs (config, history, checkpoints)
- `notebooks/`: the PINN tutorial and the reference / L2 error notebook
- `data/`: Burgers reference solutions and the JSON data the site pages read
- `results/` and `model performance/`: viscosity sweep and loss-vs-error plots
- `Finite volume solver/`: the finite-volume Burgers solver and its JS port for the race page
- `shock viewer/`, `burgers/js/`: shock-formation viewer, loss-vs-truth and viscosity pages
- `allen_cahn/`: Allen-Cahn simulator, equilibria, hilltop and correction pages
- `site/`: the assembled site, built by `scripts/build_site.py`
- `infrastructure/`: AWS CDK stack that hosts the site (S3 + CloudFront). See [`infrastructure/README.md`](./infrastructure/README.md).

## Setup

```bash
pip install -r requirements.txt
```

## Build and publish the site

```bash
python scripts/build_site.py
python scripts/publish_site.py --dry-run
python scripts/publish_site.py --bucket BUCKET --distribution DIST_ID
```
