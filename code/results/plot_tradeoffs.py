"""Figure 1 of the writeup: tastiness against four costs, with each baseline's Pareto front.

Four panels in one row. Every dot is one run (20 per baseline). In each panel a lower cost and a
higher tastiness are better, so the ideal corner is the top left. The step line joins the runs of
a baseline that no other run of that baseline beats on both axes.

Writes pareto_tradeoffs.pdf / .png to results/ and to report/figures/.

Usage:
    python plot_tradeoffs.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from load_baselines import load

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT_DIRS = [ROOT / "results", ROOT / "report" / "figures"]

GOOGLE, DEEPSEEK = "#2a78d6", "#eb6834"      # a two-colour palette checked for colour-blind separation
INK, MUTED, GRID = "#1F2933", "#5F6B76", "#E3E7EB"
PANELS = [("decide_min", "Time to decision (min)"), ("price_usd", "Price (US$)"),
          ("prep_min", "Preparation time (min)"), ("nutrition", "Nutritional value (Ofcom)")]


def front(points):
    """Non-dominated points when x is minimised and y is maximised, sorted by x."""
    keep = [p for p in points
            if not any((q[0] <= p[0] and q[1] >= p[1]) and (q[0] < p[0] or q[1] > p[1]) for q in points)]
    return sorted(set(keep))


def plot_tradeoffs(runs, out_dirs=OUT_DIRS):
    plt.rcParams.update({
        "font.family": "sans-serif", "font.sans-serif": ["Source Sans Pro", "Source Sans 3", "Helvetica Neue", "Arial"],
        "font.size": 8, "axes.edgecolor": MUTED, "axes.linewidth": 0.6, "axes.labelcolor": INK,
        "xtick.color": MUTED, "ytick.color": MUTED, "xtick.labelsize": 7.5, "ytick.labelsize": 7.5,
        "xtick.major.size": 2.5, "ytick.major.size": 0, "xtick.major.width": 0.6, "pdf.fonttype": 42,
    })
    fig, axes = plt.subplots(1, 4, figsize=(6.5, 2.3), sharey=True)
    for ax, (key, xlabel) in zip(axes, PANELS):
        for method, colour in (("google", GOOGLE), ("deepseek", DEEPSEEK)):
            pts = [(r[key], r["tastiness"]) for r in runs if r["method"] == method]
            nd = front(pts)
            rest = [p for p in pts if p not in nd]
            ax.scatter(*zip(*rest), s=15, color=colour, alpha=0.32, linewidths=0, zorder=2)
            ax.plot(*zip(*nd), color=colour, lw=1.3, drawstyle="steps-post", zorder=3, solid_joinstyle="round")
            ax.scatter(*zip(*nd), s=24, color=colour, edgecolors="white", linewidths=0.9, zorder=4)
        ax.set_xlabel(xlabel, labelpad=3)
        ax.set_ylim(0.5, 5.3)
        ax.set_yticks([1, 2, 3, 4, 5])
        ax.grid(axis="y", color=GRID, lw=0.6, zorder=0)
        ax.set_axisbelow(True)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.margins(x=0.08)
        # every panel: lower x and higher tastiness are better, so the ideal corner is the top left
        ax.annotate("", xy=(0.0, 1.115), xytext=(0.075, 1.03), xycoords="axes fraction",
                    arrowprops=dict(arrowstyle="-|>", color=MUTED, lw=0.7, shrinkA=0, shrinkB=0, mutation_scale=6.5))
        ax.text(0.095, 1.045, "better", transform=ax.transAxes, fontsize=7, color=MUTED, ha="left", va="center")
    axes[0].set_ylabel("Tastiness (0–5)", labelpad=4)
    handles = [
        Line2D([], [], marker="o", ls="", color=GOOGLE, markeredgecolor="white", markersize=5.5, label="Google Search"),
        Line2D([], [], marker="o", ls="", color=DEEPSEEK, markeredgecolor="white", markersize=5.5, label="DeepSeek"),
        Line2D([], [], color=MUTED, lw=1.3, marker="o", markersize=4.5, markeredgecolor="white",
               label="Pareto front of a baseline"),
        Line2D([], [], marker="o", ls="", color=MUTED, alpha=0.4, markersize=4.5, markeredgewidth=0, label="dominated run"),
    ]
    fig.legend(handles=handles, loc="upper center", ncol=4, frameon=False, fontsize=8, handletextpad=0.4,
               columnspacing=1.6, bbox_to_anchor=(0.5, 1.03), labelcolor=INK)
    fig.subplots_adjust(left=0.06, right=0.995, bottom=0.2, top=0.79, wspace=0.10)
    for folder in out_dirs:
        folder.mkdir(parents=True, exist_ok=True)
        fig.savefig(folder / "pareto_tradeoffs.pdf")
        fig.savefig(folder / "pareto_tradeoffs.png", dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    runs, _ = load()
    plot_tradeoffs(runs)
    print("wrote pareto_tradeoffs.pdf/.png to", ", ".join(str(d) for d in OUT_DIRS))
