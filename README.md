# The Real Singularity

A website that explains how a physics-informed neural network (PINN) works, using the viscous Burgers' equation as the running example:

$$
\frac{\partial u}{\partial t} + u \frac{\partial u}{\partial x} = \nu \frac{\partial^2 u}{\partial x^2}
$$

Live site: **https://d3hn8ndenpdwl3.cloudfront.net**
DS3 Projects, UC San Diego, Fall 2026. Charles Cheng, Michelle Zhao, Paarth Nawani, Niko Calabro. Mentor: Ryo Ide.

The site starts from this autumn's headlines, where AI is said to have settled Navier–Stokes and the Riemann
hypothesis. It then shows how AI is really used for physics: it explains neural networks and PINNs, and tests
PINNs on two problems with known exact answers.

- **Beat 1 (Burgers' equation, told as a traffic jam):** the PINN is excellent on a gentle wave (0.055% error) and
  fails on a sharp shock (about 40%). Its own training loss can improve 226× while the answer stays 35% wrong.
- **Beat 2 (Allen–Cahn, $u_t = u_{xx} + \mu(u - u^3)$):** a step-by-step simulator can never stop on an unstable
  state; a PINN can aim at one, but its loss can't tell a stable state from an unstable one.

The thread through the site is that an AI's own score is not the same as being right, so a person still has to
check and interpret the result. The same theme continues in AI-written proofs checked by Lean.

## The website

| Page | What it shows | Source file |
| --- | --- | --- |
| Home | Headline hook, neural networks and PINNs explained, the two beats, back to the headline | `site/index.html` |
| Beat 1 | The traffic story, with a live car animation | `story/beat1.html` |
| How the wall forms | Characteristics crossing into a shock | `shock viewer/index.html` |
| Our PINN, live | The trained PINN running in the browser (ONNX) | `web/index.html` |
| The breaking point | PINN vs. exact at three viscosities | `burgers/js/viscosity.html` |
| The score that lies | Training loss vs. true error | `burgers/js/loss_truth.html` |
| The race | PINN vs. finite-volume solver | `Finite volume solver/race_solver.html` |
| Beat 2 | The magnets story, stability and blow-ups | `story/beat2.html` |
| The step-by-step simulator | Allen–Cahn forward Euler and the energy ladder | `allen_cahn/js/simulator.html` |
| Falling off a hilltop | The hilltop-escape experiment | `allen_cahn/js/hilltop.html` |
| Fixing the PINN's guesses | The simulator correcting PINN guesses | `allen_cahn/js/correction.html` |

`scripts/build_site.py` copies each source into `site/` and adds what every page shares: the top bar (home, Beat 1,
Beat 2, light/dark switch), the previous / next bar, the Inter font and KaTeX for math. So **edit the source file,
not its copy in `site/`**, which is overwritten on every build. The two exceptions live only in `site/`: the
homepage `site/index.html` and the pictures in `site/images/`.

## Where to edit the text

| To change | Edit | Look for |
| --- | --- | --- |
| Homepage paragraphs | `site/index.html` | the small orange section labels: "How physics is really done with AI", "Step 1 · Neural networks", "Step 2 · How a PINN learns physics", "Step 3 · What we tested", "Step 4 · Back to the headline", "Conclusion", "Sources" |
| The two beat cards on the homepage | `site/index.html` | `class="beat"` |
| Beat 1 story | `story/beat1.html` | the `<h2>` headings, from "Traffic, treated like a fluid" to "What this tells us" |
| Beat 2 story | `story/beat2.html` | the `<h2>` headings, from "Why hilltops matter" to "Two kinds of blow-up" |
| Demo cards at the end of a beat | `story/beat1.html`, `story/beat2.html` | "Try it yourself" |
| A demo page's intro, "Try this", "What to notice", "Key takeaways", "The math, for the curious" | the page's source file (table above) | those phrases |
| Top-bar labels, which demos belong to each beat and in what order | `scripts/build_site.py` | `BEATS` |
| Pictures | add the file to `site/images/` | reference it as `images/<name>` from the homepage, `../images/<name>` from a beat page |

Math goes in as LaTeX: `\( u_t + u\,u_x = \nu\,u_{xx} \)` inside a sentence, `\[ ... \]` on its own line. A plain `$`
stays a dollar sign.

After an edit, rebuild and look at it locally, then publish:

```bash
python scripts/build_site.py
python -m http.server 8000 --directory site   # open http://localhost:8000
python scripts/deploy.py
```

## Structure

- `pinn/`: the Burgers' PINN package (model, sampling, losses, exact reference, training, run logging). See [`pinn/README.md`](./pinn/README.md).
- `scripts/`: training runs, ONNX and data exports, and the site build and publish scripts
- `runs/`: saved training runs (config, history, checkpoints)
- `notebooks/`: the PINN tutorial and the reference / L2 error notebook
- `data/`: Burgers reference solutions and the JSON data the site pages read. See [`data/README.md`](./data/README.md).
- `results/` and `model performance/`: viscosity sweep and loss-vs-error plots
- `Finite volume solver/`: the finite-volume Burgers solver and its JS port for the race page
- `shock viewer/`, `burgers/js/`: shock-formation viewer, loss-vs-truth and viscosity pages
- `web/`: the live-PINN page and its ONNX model
- `story/`: the Beat 1 and Beat 2 story pages
- `allen_cahn/`: Allen-Cahn simulator, equilibria, hilltop and correction pages. See [`allen_cahn/js/README.md`](./allen_cahn/js/README.md).
- `site/`: the assembled site, built by `scripts/build_site.py`
- `infrastructure/`: AWS CDK stack that hosts the site (S3 + CloudFront). See [`infrastructure/README.md`](./infrastructure/README.md).

## Setup

```bash
pip install -r requirements.txt
```

## Build and publish the site

```bash
python scripts/build_site.py
python scripts/deploy.py                  # build, sign in to AWS, upload, refresh CloudFront
python scripts/deploy.py --dry-run        # build and list what would be uploaded
```

`deploy.py` reads the bucket and distribution from the `BurgersSiteStack` outputs. To pass them by hand instead:

```bash
python scripts/publish_site.py --dry-run
python scripts/publish_site.py --bucket BUCKET --distribution DIST_ID
```

## Reproduce the experiments

```bash
python scripts/run.py --help              # one training run, saved to runs/<name>/
python scripts/show_results.py            # error table and plots for the main runs
node allen_cahn/js/check_ac.js            # Allen-Cahn simulator checks
```
