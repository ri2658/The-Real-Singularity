# Allen–Cahn JS simulator (Beat 2)

Forward Euler for `u_t = u_xx + mu (u - u^3)` on `(0, pi)`, `u = 0` at both ends,
`mu = 6`, `N = 128` (127 interior points), `dt = 0.4 h^2` by default.

| File | What it is |
| --- | --- |
| `allen_cahn.js` | The simulator: grid, `rhs` (= F(U)), `energy`, `createSimulator`, `simulate`. Works in the browser and in Node. |
| `check_ac.js` | Checks against Table 1 / Table 2 of the notes, plus Michelle's `equilibria.json` once it exists. |
| `simulator.html` | Test page: animated u(x), energy vs time, Δt slider (blow-up demo), hilltop-escape preset. |
| `hilltop.js` | Hilltop experiment: unstable mode of S (power iteration) and escape time from S + ε·v. |
| `hilltop_experiment.js` | Runs ε = 1e-2 … 1e-12 for three escape thresholds and both push directions; writes `data/allen_cahn/hilltop_escape.json`. Plot with `python scripts/plot_hilltop.py`. |

## Hilltop result (week-6 success check)

Escape time from S grows **1.5058 per decade** of ε, against the theory value ln 10 / λ₁ = **1.5056**.
The 0.0002 gap is forward Euler itself: each step multiplies the push by (1 + Δt·λ₁), so the
effective rate is ln(1 + Δt·λ₁)/Δt and the expected slope is 1.50584, matched to 4e-5.
The slope does not depend on the escape threshold (0.05, 0.1, 0.3) or the push direction.
At ε = 1e-12 the push is close to round-off in S itself, and the point drifts off the line by 0.005.

## Run the checks (PowerShell, from the repo root)

```powershell
node allen_cahn/js/check_ac.js
```

## Open the page

```powershell
python -m http.server
```

Then open http://localhost:8000/allen_cahn/js/simulator.html. Serve from the repo root
so the page can also load `data/allen_cahn/equilibria.json` and `pinn_guesses.json`
(they show up in the "Starting curve" list once those files exist).
