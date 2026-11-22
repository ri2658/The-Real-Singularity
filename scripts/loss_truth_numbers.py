"""Print every number that the loss-vs-truth page, Beat 1, the home page and the README
quote about "the score that lies", straight from data/loss_truth/runs.json.

Run from the repo root after scripts/export_loss_truth.py:
    python scripts/loss_truth_numbers.py

Terms:
    own score    the logged training loss (on the run's own 10,000 check points)
    new score    the same loss with the PDE term re-graded on 200,000 new points
    before       median over Adam steps 1500-2000 (the last single Adam value is noisy)
    switch       step 2000, where training changes from Adam to L-BFGS
"""

import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SWITCH = 2000
SETTLE = 500        # "first ~500 steps after the switch"


def at(r, key, step):
    """Logged value at the first log step >= step."""
    i = next(i for i, s in enumerate(r["step"]) if s >= step)
    return r[key][i]


def before(r, key):
    return statistics.median(v for s, v in zip(r["step"], r[key]) if SWITCH - 500 <= s <= SWITCH)


def ranks(v):
    order = sorted(range(len(v)), key=lambda i: v[i])
    out = [0.0] * len(v)
    for k, i in enumerate(order):
        out[i] = float(k)
    return out


def spearman(a, b):
    ra, rb = ranks(a), ranks(b)
    ma, mb = statistics.fmean(ra), statistics.fmean(rb)
    cov = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    return cov / math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))


def pct(v):
    return f"{100 * v:.1f}%"


def main():
    data = json.loads((ROOT / "data" / "loss_truth" / "runs.json").read_text())
    runs = data["runs"]
    fp = data["fresh_points"]
    print(f"new points: {fp['n']:,} uniform points, seed {fp['seed']}\n")

    print("1. Every run at the end of training")
    print(f"  {'run':22s} {'own score':>10s} {'new score':>10s} {'new/own':>9s} "
          f"{'own pde':>9s} {'new pde':>9s} {'pde x':>8s} {'error':>7s} {'jump x':>7s}")
    for r in runs:
        lo, ln = r["loss"][-1], r["fresh"]["loss"][-1]
        po, pn = r["loss_pde"][-1], r["fresh"]["pde"][-1]
        print(f"  {r['name']:22s} {lo:10.2e} {ln:10.2e} {ln / lo:9.3g} {po:9.2e} {pn:9.2e} "
              f"{pn / po:8.3g} {pct(r['err'][-1]):>7s} {r['jump_x']:+7.3f}")

    print("\n2. New/own PDE ratio at the Adam checkpoints (steps 0-2000)")
    for samp in ("uniform", "shock"):
        rs = [r for r in runs if r["sampling"] == samp]
        vals = [p / at(r, "loss_pde", s) for r in rs
                for s, p in zip(r["fresh"]["step"], r["fresh"]["pde"]) if s <= SWITCH]
        print(f"  {samp:8s} runs: {min(vals):.2f} to {max(vals):.2f}")

    trap = [r for r in runs if r["nu_pi"] == 0.003 and r["sampling"] == "uniform" and r["lbfgs"]]
    shock3 = [r for r in runs if r["nu_pi"] == 0.003 and r["sampling"] == "shock"]

    print("\n3. The trap: medium fluid (nu = 0.003/pi), evenly spread points")
    for r in trap:
        lb, eb = before(r, "loss"), before(r, "err")
        l1, e1 = at(r, "loss", SWITCH + SETTLE), at(r, "err", SWITCH + SETTLE)
        lf, ef = r["loss"][-1], r["err"][-1]
        pn, po = r["fresh"]["pde"][-1], r["loss_pde"][-1]
        print(f"  {r['name']}")
        print(f"    score on own points: {lf:.2g}   on new points: {r['fresh']['loss'][-1]:.2g} "
              f"({r['fresh']['loss'][-1] / lf:,.0f}x); PDE term alone {pn:.2g} vs {po:.2g} ({pn / po:,.0f}x)")
        print(f"    before the switch (median, steps 1500-2000): score {lb:.2g}, error {pct(eb)}")
        print(f"    error at steps 1800 / 1900 / 2000: {pct(at(r, 'err', 1800))} / "
              f"{pct(at(r, 'err', 1900))} / {pct(at(r, 'err', 2000))}")
        print(f"    switch -> end (step {r['step'][-1]}): score fell {lb / lf:.0f}x "
              f"(residual size, its square root, {math.sqrt(lb / lf):.1f}x); error {pct(eb)} -> {pct(ef)}")
        print(f"    first {SETTLE} steps after the switch: score fell {lb / l1:.0f}x, error {pct(eb)} -> {pct(e1)}")
        print(f"    then the last {r['step'][-1] - SWITCH - SETTLE:,} steps: score fell {l1 / lf:.0f}x, "
              f"error {pct(e1)} -> {pct(ef)}")
        print(f"    old headline (single step-2000 value): score fell {at(r, 'loss', SWITCH) / lf:.0f}x, "
              f"error fell {at(r, 'err', SWITCH) / ef:.2f}x")
        print(f"    jump at t = 1: x = {r['jump_x']:+.3f} (exact: x = 0)")

    print("\n4. Same fluid, extra points at the jump (uses our prior knowledge that the jump forms at x = 0)")
    for r in shock3:
        print(f"  {r['name']}: error {pct(r['err'][-1])}, new/own PDE at the end "
              f"{r['fresh']['pde'][-1] / r['loss_pde'][-1]:.2f}, jump at x = {r['jump_x']:+.3f}")

    print("\n5. Thin fluid (nu = 0.001/pi), evenly spread points")
    for r in runs:
        if r["nu_pi"] == 0.001 and r["sampling"] == "uniform" and r["lbfgs"]:
            lb, eb = before(r, "loss"), before(r, "err")
            print(f"  {r['name']}: score fell {lb / r['loss'][-1]:.1f}x, error {pct(eb)} -> {pct(r['err'][-1])} "
                  f"(fell {eb / r['err'][-1]:.2f}x); final score {r['loss'][-1]:.1g}")
    thin = [r for r in runs if r["nu_pi"] == 0.001 and r["sampling"] in ("uniform", "shock")]
    good = [r for r in runs if r["err"][-1] < 0.05]
    best_good = max(r["loss"][-1] for r in good)
    print(f"  all thin-fluid runs: final score {min(r['loss'][-1] for r in thin):.1g} to "
          f"{max(r['loss'][-1] for r in thin):.1g}, error {pct(min(r['err'][-1] for r in thin))} to "
          f"{pct(max(r['err'][-1] for r in thin))}")
    print(f"  thin-fluid final score / highest score of any run under 5% error ({best_good:.2g}): "
          + ", ".join(f"{r['loss'][-1] / best_good:.0f}x" for r in thin))
    print("  thin-fluid new/own score at the end: "
          + ", ".join(f"{r['fresh']['loss'][-1] / r['loss'][-1]:.0f}x" for r in thin))

    print("\n6. Check points that move during training (no prior knowledge of the jump)")
    for samp, what in (("rad", "packed where the equation is broken worst"), ("resample", "redrawn evenly")):
        rs = [r for r in runs if r["sampling"] == samp]
        if not rs:
            print(f"  {samp}: no runs yet")
            continue
        print(f"  {samp} ({what}):")
        for r in rs:
            ratios = [p / at(r, "loss_pde", s) for s, p in zip(r["fresh"]["step"], r["fresh"]["pde"])]
            first = [x for s, x in zip(r["fresh"]["step"], ratios) if SWITCH < s <= SWITCH + 1000]
            later = [x for s, x in zip(r["fresh"]["step"], ratios) if s > SWITCH + 1000]
            print(f"    {r['name']:22s} error {pct(r['err'][-1]):>6s}  own score {r['loss'][-1]:.2g}  "
                  f"new score {r['fresh']['loss'][-1]:.2g}  new/own PDE at the end {ratios[-1]:.2f}; "
                  f"first L-BFGS round up to {max(first):.1f}, after it {min(later):.2f} to {max(later):.2f}; "
                  f"jump at x = {r['jump_x']:+.3f}")
        e = sorted(r["err"][-1] for r in rs if r["nu_pi"] == 0.003)
        if e:
            print(f"    nu = 0.003/pi: error {pct(e[0])} to {pct(e[-1])}")

    print("\n7. Control: fixed evenly spread points, Adam only (no L-BFGS)")
    ctrl = [r for r in runs if not r["lbfgs"]]
    if not ctrl:
        print("  no runs yet")
    for r in ctrl:
        ratios = [p / at(r, "loss_pde", s) for s, p in zip(r["fresh"]["step"], r["fresh"]["pde"])]
        late = [e for s, e in zip(r["step"], r["err"]) if s >= 10000]
        print(f"  {r['name']:22s} {r['step'][-1]:,} steps: final error {pct(r['err'][-1])} (best {pct(min(r['err']))}); "
              f"after step 10,000 the error is {pct(min(late))} to {pct(max(late))}, median "
              f"{pct(statistics.median(late))}; lowest score {min(r['loss']):.2g}; new/own PDE at the end "
              f"{ratios[-1]:.0f}, largest {max(ratios):.0f} at step {r['fresh']['step'][ratios.index(max(ratios))]:,}")
    rerun = ROOT / "runs" / "nu0.003_vanilla_s2_gpu" / "history.json"
    if ctrl and rerun.exists():
        # Work done, counted in loss + gradient evaluations (logged since week 5). The CPU trap runs
        # predate that log, so the GPU rerun of the trap (same config, seed 2) stands in for them.
        h = json.loads(rerun.read_text())
        lb = h[-1]["evals"] - next(e["evals"] for e in h if e["step"] == SWITCH)
        adam = 50_000 - SWITCH
        print(f"  work after step {SWITCH}: the trap's L-BFGS phase (GPU rerun, nu0.003_vanilla_s2_gpu) used {lb:,} "
              f"loss + gradient evaluations in {h[-1]['step'] - SWITCH:,} steps; Adam only used {adam:,}, "
              f"{adam / lb:.1f}x as many")
    if ctrl:
        print(f"  for comparison, the trap runs end with new/own PDE "
              + ", ".join(f"{r['fresh']['pde'][-1] / r['loss_pde'][-1]:,.0f}" for r in trap)
              + " and scores " + ", ".join(f"{r['loss'][-1]:.2g}" for r in trap))

    print("\n8. The scatter (all runs, final values)")
    old = [r for r in runs if r["sampling"] in ("uniform", "shock") and r["lbfgs"]]
    err = [r["err"][-1] for r in old]
    print(f"  the 20 week-3/4 runs: rank correlation, own score vs. error: "
          f"{spearman([r['loss'][-1] for r in old], err):.2f}")
    print(f"  the 20 week-3/4 runs: rank correlation, new score vs. error: "
          f"{spearman([r['fresh']['loss'][-1] for r in old], err):.2f}")
    print(f"  trap runs: own score {min(r['loss'][-1] for r in trap):.2g} to {max(r['loss'][-1] for r in trap):.2g}, "
          f"new score {min(r['fresh']['loss'][-1] for r in trap):.2g} to "
          f"{max(r['fresh']['loss'][-1] for r in trap):.2g}, error {pct(min(r['err'][-1] for r in trap))} to "
          f"{pct(max(r['err'][-1] for r in trap))}")
    print(f"  every other week-3/4 run: new score at most "
          f"{max(r['fresh']['loss'][-1] for r in old if r not in trap):.2g}")
    print(f"  trap runs, new/own score: " + ", ".join(
        f"{r['fresh']['loss'][-1] / r['loss'][-1]:,.0f}x" for r in trap))
    good = [r for r in runs if r["err"][-1] < 0.05]
    print(f"  runs under 5% error: own score {min(r['loss'][-1] for r in good):.2g} to "
          f"{max(r['loss'][-1] for r in good):.2g}")
    lo = min(min(r["loss"][-1], r["fresh"]["loss"][-1]) for r in runs)
    hi = max(max(r["loss"][-1], r["fresh"]["loss"][-1]) for r in runs)
    print(f"  x-range needed: {lo:.2g} to {hi:.2g} (axis 1e-7 to 1e1)")


if __name__ == "__main__":
    main()
