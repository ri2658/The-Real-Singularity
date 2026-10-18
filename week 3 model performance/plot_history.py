import csv
import json

import matplotlib.pyplot as plt


def plot_history(history_path="history.json", l2_csv=None, out_png="loss_vs_l2_s0.png"):
    """
    history_path : list of records with keys step, phase, loss_total, rel_l2, ...
    l2_csv       : optional CSV (iteration,l2) from eval_l2.py. If given, it replaces
                   the rel_l2 stored in history.json (useful to recompute it yourself).
    """
    h = json.load(open(history_path))
    steps = [r["step"] for r in h]
    loss = [r["loss_total"] for r in h]

    if l2_csv:
        with open(l2_csv) as f:
            rows = list(csv.DictReader(f))
        l2_steps = [int(r["iteration"]) for r in rows]
        l2 = [float(r["l2"]) for r in rows]
    else:
        l2_steps = steps
        l2 = [r["rel_l2"] for r in h]

    fig, ax1 = plt.subplots(figsize=(8, 4.5))
    ax1.plot(steps, loss, "b-", label="total loss")
    ax1.set_xlabel("training step")
    ax1.set_ylabel("total loss", color="b")
    ax1.set_yscale("log")
    ax1.tick_params(axis="y", labelcolor="b")

    ax2 = ax1.twinx()
    ax2.plot(l2_steps, l2, "r-", label="relative L² error")
    ax2.set_ylabel("relative L² error vs reference", color="r")
    ax2.set_yscale("log")
    ax2.tick_params(axis="y", labelcolor="r")

    # mark where Adam hands over to L-BFGS
    switch = next((r["step"] for r in h if r.get("phase") == "lbfgs"), None)
    if switch is not None:
        ax1.axvline(switch, color="gray", ls="--", lw=1)
        ax1.text(switch, ax1.get_ylim()[1], " L-BFGS starts", va="top", color="gray")

    # Week 3 target
    ax2.axhline(1e-3, color="green", ls=":", lw=1)
    ax2.text(steps[0], 1e-3, " target 1e-3", va="bottom", color="green")

    ax1.set_title("Training loss vs. true error")
    fig.tight_layout()
    fig.savefig(out_png, dpi=150)
    plt.show()


if __name__ == "__main__":
    plot_history("/Users/yiwenzhao/The-Real-Singularity/runs/lbfgs_8x20_s1/history.json",out_png="loss_vs_l2_s1.png")
    # plot_history("history.json", l2_csv="l2_history.csv")   # use your own L2 values
