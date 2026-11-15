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
cp website-update/story/beat2.html                     story/beat2.html

git diff --stat                                        # check: only the files listed below
python scripts/deploy.py                               # rebuild site/ and publish
```

If you changed one of these files after e2a0201, don't copy it over yours: apply the
change from the list below by hand instead.

## Changes

| File | Change | Why |
| --- | --- | --- |
| `allen_cahn/js/simulator.html` | (1) New starting curve **"flat + tiny nudge"**: 1e-10 · sin(x), one `<option>` line and one `startCurve` line (next to `"S-push"`). (2) New **energy ladder** figure under "2. The rule: always roll downhill": the five exact resting shapes at their real energies (0, −0.35, −2.40) with downhill arrows. Its own small script at the end of the page, reading `equilibria.json`; it hides itself if the file can't be loaded. (3) **Wording**: part 1 is now "A rod of tiny magnets" (+1 up, −1 down, 0 neither way) instead of the oil-and-water mixture, and the plot label says "Which way the magnets point along the rod", to match Beat 2. Apart from those 4 lines, only additions. | (1) Flat is a hilltop too, but exact zeros never round, so with no nudge it never moves; with this nudge it sits still until t ≈ 4 and is in the hump by t ≈ 5, about four times sooner than the S-shape falls. (2) Shows section 2's rule in one picture: every shape can only move down the ladder, so every run ends in a hump. Both checked in a browser, desktop and phone, no errors from the new code. |
| `Finite volume solver/race_solver.html` | PINN error cells use the same `pct()` format as the solver column. | The table mixed formats (solver "0.32%", PINN "5.46e-4"). Now the PINN shows 0.055% / 0.080% at ν = 0.01/π. Two lines changed. |
| `story/beat2.html` | **New story order**, opening with an example anyone can follow: (1) *Why hilltops matter: how things change shape*: proteins switch shapes over a transition state (the 2025 PINN-MEP result), with a cartoon protein animation; (2) *A rod of tiny magnets*: Allen–Cahn as magnets, the five resting shapes, a nudge mini-demo, and the rod making the same switch as the protein (lowest-energy path, barrier 2.05); (3) your demo cards; (4) your *So far*; (5) *Going deeper: PINNs and blow-ups*, after the conclusion for interested readers: *From a steep wall to a blow-up* (bridge from Beat 1), *Why blow-ups matter* ($1,000,000 stat box) and *Two kinds of blow-up*. **Figures**, drawn in the page with no libraries: cartoon protein (closed → strained transition state → open, labelled as a cartoon); the five resting shapes with compass needles; nudge mini-demo (hump settles back by t ≈ 0.7, S falls into a hump by t ≈ 5); the rod's switching path with energy along it; the steep wall at three viscosities plus our PINN; bowl vs hilltop sketch. The cartoon and the rod animation share one timeline (either set of controls drives both) and don't autoplay for visitors who ask for reduced motion. **Wording**: description, opening paragraph and the hilltop card say rod/magnets instead of oil-and-vinegar; all text tightened (about 20% shorter); and your *So far* is rewritten as bullets that add the PINN limits Beat 2 found (can't tell a bowl from a hilltop; a near-perfect score for the useless flat answer). One new sentence before the nudge demo names the methods: the simulator is forward Euler on 128 pieces of the rod; the exact resting shapes come from Newton's method. Your demo cards are unchanged apart from "Balance the rod". | Readers get the "why" from a familiar example first (proteins changing shape), then the rod, then the demos; the blow-up physics comes last for those who want it. Allen–Cahn doesn't keep the amounts of each material fixed, which magnets match and a mixture doesn't. Data: the wall figure uses the existing reference and viscosity files plus exact Cole–Hopf curves near the wall (embedded; they match the reference files to 5e-7); the rod figures use equilibria.json. Facts checked against arXiv 2509.14185, the DeepMind blog, Physics World and arXiv 2504.16381 (PINN-MEP). Tested on desktop and phone, light and dark, no console errors. Beat 1 files untouched. |

Optional text for the simulator's "Try this" box, if you want it:
> Pick *flat + tiny nudge*: a push of 0.0000000001 is enough, and it falls into the hump
> about four times sooner than the S-shape.

