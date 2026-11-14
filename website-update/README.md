# website-update

Michelle's changes for the live site, ready to drop in. Every file here sits at its
real path in the repo, and each one started from Charles's latest version
(`origin/charles`, commit e2a0201, Nov 13), so copying it in changes only the lines
listed below.

## How to apply (Charles)

```bash
git fetch origin
git checkout origin/michelleZhao -- website-update     # bring in only this folder

# copy each changed file to its real path (named one by one, so this README stays here)
cp website-update/allen_cahn/js/simulator.html          allen_cahn/js/simulator.html
cp "website-update/Finite volume solver/race_solver.html" "Finite volume solver/race_solver.html"

git diff --stat                                        # check: only the files listed below
python scripts/deploy.py                               # rebuild site/ and publish
```

If you changed one of these files after e2a0201, don't copy it over yours: apply the
change from the list below by hand instead.

## Changes

| File | Change | Why |
| --- | --- | --- |
| `allen_cahn/js/simulator.html` | New starting curve **"flat + tiny nudge"**: 1e-10 · sin(x). One `<option>` line and one `startCurve` line (next to `"S-push"`). | Flat is a hilltop too, but exact zeros never round, so with no nudge it never moves. With this nudge it sits still until t ≈ 4 and is in the hump by t ≈ 5: about four times sooner than the S-shape falls (escape rate 5 vs 1.53). Checked in a browser: energy 0 → −2.4036, no console errors. |
| `Finite volume solver/race_solver.html` | PINN error cells use the same `pct()` format as the solver column. | The table mixed formats (solver "0.32%", PINN "5.46e-4"). Now the PINN shows 0.055% / 0.080% at ν = 0.01/π. Two lines changed. |

Optional text for the simulator's "Try this" box, if you want it:
> Pick *flat + tiny nudge*: a push of 0.0000000001 is enough, and it falls into the hump
> about four times sooner than the S-shape.
