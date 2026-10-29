# Allen–Cahn JS simulator (Beat 2)

Forward Euler for `u_t = u_xx + mu (u - u^3)` on `(0, pi)`, `u = 0` at both ends,
`mu = 6`, `N = 128` (127 interior points), `dt = 0.4 h^2` by default.

| File | What it is |
| --- | --- |
| `allen_cahn.js` | The simulator: grid, `rhs` (= F(U)), `energy`, `createSimulator`, `simulate`. Works in the browser and in Node. |
| `check_ac.js` | Checks against Table 1 / Table 2 of the notes, plus Michelle's `equilibria.json` once it exists. |
| `simulator.html` | Test page: animated u(x), energy vs time, Δt slider (blow-up demo), hilltop-escape preset. |

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
