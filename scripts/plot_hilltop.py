"""Plot the hilltop escape-time experiment.

Reads data/allen_cahn/hilltop_escape.json (from allen_cahn/js/hilltop_experiment.js)
and writes results/hilltop_escape.png:
    left:  escape time vs push size eps (log axis), one line per escape threshold,
           with the theory slope ln(10) / lambda_1 drawn through each
    right: deviation from the forward-Euler-corrected theory line. Forward Euler
           grows the push by (1 + dt * lambda_1) per step, i.e. at the effective rate
           ln(1 + dt * lambda_1) / dt ~ lambda_1 - dt * lambda_1^2 / 2, so the slope the
           simulator should show is ln(10) / that rate (1.5058 instead of 1.5056).

Run from the repo root:
    python scripts/plot_hilltop.py
"""

import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
INK, INK_MUTED, GRID = "#0b0b0b", "#6b6a64", "#e4e3de"
COLORS = {0.05: "#2a78d6", 0.1: "#eb6834", 0.3: "#1f9e78"}


def style(ax):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(INK_MUTED)
    ax.tick_params(colors=INK_MUTED, labelcolor=INK)
    ax.grid(True, color=GRID, lw=0.8)
    ax.set_axisbelow(True)


def main():
    d = json.loads((ROOT / "data" / "allen_cahn" / "hilltop_escape.json").read_text())
    theory = d["theory_slope"]
    h = math.pi / 128
    dt = 0.4 * h * h
    lam = d["theory_lambda"]
    euler = math.log(10) / (math.log1p(dt * lam) / dt)     # slope forward Euler should give
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(11, 4.4), gridspec_kw={"width_ratios": [1.4, 1]})
    style(ax)
    style(ax2)

    for run in d["runs"]:
        if run["sign"] < 0:
            continue                                   # +v and -v overlap; plot +v only
        delta = run["delta"]
        k = np.array([r["k"] for r in run["rows"]], float)
        T = np.array([r["T"] for r in run["rows"]])
        eps = 10.0 ** -k
        c = COLORS[delta]
        # Theory line with the measured intercept: T = a + theory * k (fit a on k <= 11).
        sel = k <= 11
        a = np.mean(T[sel] - theory * k[sel])
        ax.plot(eps, a + theory * k, color=c, lw=1, ls="--")
        ax.plot(eps, T, "o", color=c, ms=6, markeredgecolor="white", markeredgewidth=1,
                label=f"escape threshold {delta}")
        slope = np.polyfit(k[sel], T[sel], 1)[0]
        b = np.mean(T[sel] - euler * k[sel])
        ax2.plot(k, T - (b + euler * k), "o-", color=c, ms=5, lw=1.5,
                 label=f"threshold {delta}: measured slope {slope:.5f}")

    ax.set_xscale("log")
    ax.invert_xaxis()
    ax.set_xlabel("push size ε (start at S + ε·v)", color=INK)
    ax.set_ylabel("escape time", color=INK)
    ax.set_title(f"Escape time grows {theory:.4f} per decade of ε (theory ln 10 / λ₁)",
                 color=INK, fontsize=11)
    ax.legend(frameon=False, fontsize=9, loc="upper left")

    ax2.axhline(0, color=INK_MUTED, lw=1)
    ax2.set_xlabel("decades k (ε = 10⁻ᵏ)", color=INK)
    ax2.set_ylabel("escape time minus Euler-corrected line", color=INK)
    ax2.set_title(f"Residual vs. forward-Euler slope {euler:.5f}", color=INK, fontsize=11)
    ax2.annotate("ε = 1e-12: near the\nround-off floor", (12, -0.005), xytext=(9.2, -0.0042),
                 fontsize=8, color=INK_MUTED, arrowprops=dict(arrowstyle="->", color=INK_MUTED, lw=0.8))
    ax2.legend(frameon=False, fontsize=8, loc="lower left")

    fig.suptitle(f"Hilltop escape from the S state (λ₁ = {d['measured_lambda']:.4f})", color=INK)
    fig.tight_layout()
    out = ROOT / "results" / "hilltop_escape.png"
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=150)
    print(f"saved {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
