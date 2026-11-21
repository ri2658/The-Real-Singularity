# The Real Singularity

**What AI that learns physics can and can't do, tested with demos you can play with.**
Live site: **https://d3hn8ndenpdwl3.cloudfront.net**

DS3 Projects, UC San Diego, Fall 2026. Charles Cheng, Michelle Zhao, Paarth Nawani, Niko Calabro. Mentor: Ryo Ide.

---

## The hook

In September 2026, OpenAI announced that its AI had settled a Navier–Stokes Millennium Prize Problem, a
$1,000,000 question about whether the equations of fluid flow can blow up. In November, an Anthropic researcher
announced that he and Claude had proved the Riemann hypothesis, in 17 million lines of Lean. It can seem like AI
can do anything now, even the hardest problems in mathematical physics.

But that is not how most physics actually gets done with AI. Day to day, scientists train neural networks to
predict how fluids, traffic or materials behave. A popular approach is the **physics-informed neural network
(PINN)**, which learns from the equation itself instead of from worked examples. We built PINNs, tested them on two
problems where the exact answer is known, and checked every result.

**Our thread: an AI's own score is not the same as being right.** PINNs are genuinely powerful, but they fail in a
systematic way: the loss they train on can look excellent while the answer is wrong. Someone still has to set up the
question, check the score against something independent, and interpret the answer. The same theme continues in
AI-written proofs, where a passing Lean check is not the same as a proof people have confirmed.

We are not debunking AI. We are trying to show where it is truly revolutionary, and where its abilities are
overstated.

## What we did

### How a PINN works (homepage, Steps 1–2)

A network $u_\theta(x, t)$ (8 layers of 20 tanh neurons, 3,021 parameters) is trained by gradient descent to make
the equation's residual small at 10,000 random points, plus the starting state and the boundary:

$$L(\theta) = \frac{1}{N_r}\sum_i r_\theta(x_i, t_i)^2 + \frac{1}{N_0}\sum_j \big(u_\theta(x_j, 0) - u_0(x_j)\big)^2 + \frac{1}{N_b}\sum_k u_\theta(\pm 1, t_k)^2 .$$

No exact answer goes into the loss. We measure accuracy separately, as the relative $L^2$ error against the exact
solution; every percentage on the site is that number.

### Beat 1: The wall of brake lights (Burgers' equation)

$$u_t + u\,u_x = \nu\,u_{xx}, \qquad u(x, 0) = -\sin(\pi x), \quad u(\pm 1, t) = 0.$$

Burgers' equation is the one-dimensional cousin of Navier–Stokes, and with a change of variables it is also the
classic model of a traffic jam: a smooth slowdown that sharpens into a wall (a shock). Smaller viscosity $\nu$
means a sharper wall.

| Finding | Number |
| --- | --- |
| Gentle wall ($\nu = 0.01/\pi$): the PINN is excellent | 0.055% error |
| Sharp wall ($\nu = 0.001/\pi$): the PINN fails, even with extra training points at the wall | about 40% error |
| The PINN's own loss can't tell: in one run it improved 226× while the answer stayed wrong | 35% error |
| A traditional finite-volume solver on the sharp wall, in the browser | 0.17% error in 63 ms |

### Beat 2: Balls in bowls, balls on hilltops (Allen–Cahn)

$$u_t = u_{xx} + \mu\,(u - u^3) \quad \text{on } (0, \pi), \qquad u = 0 \text{ at both ends}, \quad \mu = 6.$$

A rod of tiny magnets has five resting shapes: two stable (balls in bowls) and three unstable (balls on hilltops).

- A step-by-step simulator is gradient descent on the energy, so it always rolls downhill and can never stop on a
  hilltop. A ball nudged off the hilltop takes $\ln 10/\lambda_1 = 1.5056$ more time units for every 10× smaller
  nudge; we measured 1.5058.
- A PINN can aim straight at hilltop shapes. But its loss is just as good for a bowl as for a hilltop, and nearly
  perfect for a useless flat answer. Handing its guesses to the simulator shows which ones hold up.

### Back to the headline

OpenAI released its Navier–Stokes proof with a Lean version. Mathematicians at Cambridge showed that the Lean
version checks a slightly different statement from the written proof. That does not make the result wrong, but the
machine check did not confirm the proof people read. In both PINNs and AI proofs, a person closes the gap.

## The website

| Page | What it shows | Source file |
| --- | --- | --- |
| Home | The hook, neural networks and PINNs explained, the two beats, back to the headline | `site/index.html` |
| Beat 1 | The traffic story, with a live car animation | `story/beat1.html` |
| How the wall forms | Characteristics crossing into a shock | `shock viewer/` |
| Our PINN, live | The trained PINN running in the browser (ONNX) | `web/` |
| The breaking point | PINN vs. exact at three viscosities | `burgers/js/viscosity.html` |
| The score that lies | Training loss vs. true error over training | `burgers/js/loss_truth.html` |
| The race | PINN vs. finite-volume solver, head to head | `Finite volume solver/race_solver.html` |
| Beat 2 | The magnets story, stability, and blow-ups | `story/beat2.html` |
| The step-by-step simulator | Allen–Cahn forward Euler, energy ladder | `allen_cahn/js/simulator.html` |
| Falling off a hilltop | The hilltop-escape experiment | `allen_cahn/js/hilltop.html` |
| Fixing the PINN's guesses | The simulator correcting PINN guesses | `allen_cahn/js/correction.html` |

Every page is plain HTML and JavaScript with no framework. Math is written as `\( … \)` or `\[ … \]` and rendered
by KaTeX; the whole site uses one font, Inter; the light / dark switch is in the top-right corner.

### How the pieces fit

```
page sources (story/, web/, burgers/js/, allen_cahn/js/, ...)  +  data/
        │   python scripts/build_site.py
        ▼
site/   ← adds the top bar, the previous/next bar, the font, KaTeX and the theme switch to every page
        │   python scripts/deploy.py
        ▼
S3 + CloudFront (infrastructure/)  →  https://d3hn8ndenpdwl3.cloudfront.net
```

`site/index.html` (the homepage) and `site/images/` are edited in place; everything else in `site/` is generated,
so edit the source file, not the copy in `site/`.

### Work on the site

```bash
python scripts/build_site.py                 # rebuild site/ after any change
python -m http.server 8000 --directory site  # then open http://localhost:8000
python scripts/deploy.py                     # build, sign in to AWS, upload, refresh CloudFront
```

To add a picture to a beat page, put it in `site/images/` (WebP or JPEG, a few hundred KB at most) and reference it
from `story/beat1.html` or `story/beat2.html` as `../images/<name>`.

## Repository layout

| Folder | Contents |
| --- | --- |
| `pinn/` | The Burgers PINN in PyTorch: model, training points, losses, exact reference, training loop, run logging |
| `scripts/` | Run experiments (`run.py`, `reproduce_baseline.py`), export data for the site (`export_*.py`), plots, build and deploy |
| `runs/` | Every training run: config, loss and error history, checkpoints, summary |
| `results/` | Figures and tables from the experiments |
| `data/` | References, exported predictions and ONNX models used by the site (see `data/README.md`) |
| `Finite volume solver/` | The traditional solver (Python and JavaScript) and the race page |
| `shock viewer/` | The shock-formation page |
| `burgers/js/` | The breaking-point and score-that-lies pages |
| `allen_cahn/js/` | The Allen–Cahn simulator, hilltop experiment and correction pages (see its README) |
| `web/` | The live-PINN page and its ONNX model |
| `story/` | The Beat 1 and Beat 2 story pages |
| `site/` | The built website |
| `infrastructure/` | AWS CDK stack for hosting (S3 + CloudFront) |
| `notebooks/` | The original PINN tutorial notebook |

## Reproduce the experiments

```bash
pip install -r requirements.txt
python scripts/reproduce_baseline.py   # checks pinn/ against the original tutorial network
python scripts/run.py --help           # any single run, saved to runs/<name>/
python scripts/show_results.py         # error table and plots for the main runs (runs/p1000_8x20_s*)
node allen_cahn/js/check_ac.js         # Allen–Cahn simulator checks
```

## Sources

- Navier–Stokes priority controversy, Wikipedia; CNBC, Sept 9, 2026.
- Bastounis, Circelli and Hansen, "Navier-Stokes lost in translation: Why Lean verification of AI
  autoformalisation does not guarantee correct natural language proofs", arXiv 2610.08144, Oct 2026.
- Al Jazeera, Nov 21, 2026; Washington Post, Nov 20, 2026 (the Riemann hypothesis claim, unverified at the time of
  writing).
- Raissi, Perdikaris and Karniadakis, "Physics-informed neural networks", J. Comput. Phys. 378 (2019), 686–707.
- LeVeque et al., *Riemann Problems and Jupyter Solutions*: Traffic flow (the Lighthill–Whitham–Richards model).
