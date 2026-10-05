"""First-pass results for the two baselines: tables, Pareto analysis and the trade-off figure.

Reads Baselines.xlsx (through load_baselines.py) and writes
    output/baselines_clean.csv          one line per run, every metric as a number
    ../../report/generated/*.tex        table rows and numbers used by the writeup
    ../../report/figures/pareto_tradeoffs.pdf

Usage:
    python analyze_baselines.py
"""
import csv
import statistics as st
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from load_baselines import METRICS, load

HERE = Path(__file__).resolve().parent
REPORT = HERE.parents[1] / "report"
GEN, FIG, OUT = REPORT / "generated", REPORT / "figures", HERE / "output"

GOOGLE, DEEPSEEK = "#2a78d6", "#eb6834"      # categorical slots 1 and 2 (validated, colour-blind safe)
INK, MUTED, GRID = "#1F2933", "#5F6B76", "#E3E7EB"
NAME = {"google": "Google Search", "deepseek": "DeepSeek"}
SHORT_HEAD = {"shop_min": "Shop", "prep_min": "Prep", "price_usd": "Price", "tastiness": "Taste",
              "nutrition": "Nutr.", "diet_violation": "Diet", "decide_min": "Decide"}


# ---------------------------------------------------------------- comparisons
def advantage(pair, key, sign):
    """> 0 if DeepSeek is better on this metric for this scenario, < 0 if Google is, 0 for a tie."""
    return (pair["deepseek"][key] - pair["google"][key]) * sign


def dominance(pair):
    """Pareto comparison of the two runs of one scenario over all seven metrics."""
    adv = [advantage(pair, key, sign) for key, _, _, _, sign in METRICS]
    if all(a >= 0 for a in adv) and any(a > 0 for a in adv):
        return "deepseek"
    if all(a <= 0 for a in adv) and any(a < 0 for a in adv):
        return "google"
    return "tradeoff"


def summarise(pairs):
    rows = []
    for key, _, label, unit, sign in METRICS:
        g = [p["google"][key] for p in pairs]
        d = [p["deepseek"][key] for p in pairs]
        adv = [advantage(p, key, sign) for p in pairs]
        rows.append(dict(key=key, label=label, unit=unit, sign=sign, google=st.mean(g), deepseek=st.mean(d),
                         diff=st.mean(d) - st.mean(g), google_wins=sum(a < 0 for a in adv),
                         ties=sum(a == 0 for a in adv), deepseek_wins=sum(a > 0 for a in adv)))
    return rows


# ---------------------------------------------------------------- formatting
def mmss(minutes):
    total = round(abs(minutes) * 60)
    return f"{total // 60}:{total % 60:02d}"


def fmt(key, x, signed=False):
    s = ("+" if x > 0 else "−" if x < 0 else "") if signed else ("−" if x < 0 else "")
    a = abs(x)
    if key == "decide_min":
        body = mmss(a)
    elif key == "diet_violation":
        body = f"{100 * a:.0f}" + (" pp" if signed else r"\%")
    elif key == "price_usd":
        body = f"{a:.2f}"
    elif key in ("shop_min", "prep_min"):
        body = f"{a:.1f}"
    else:
        body = f"{a:.2f}"
    return (s + body).replace("−", "$-$")


UNIT_TEX = {"min": "min", "US$": r"US\$", "0-5": "0--5", "Ofcom score": "Ofcom score", "0/1": "share"}


def write_tex(pairs, rows):
    GEN.mkdir(parents=True, exist_ok=True)

    # --- scorecard: one line per metric
    lines = []
    for r in rows:
        unit = "min:sec" if r["key"] == "decide_min" else UNIT_TEX[r["unit"]]
        g, d = fmt(r["key"], r["google"]), fmt(r["key"], r["deepseek"])
        better = None if r["google"] == r["deepseek"] else ("deepseek" if (r["deepseek"] - r["google"]) * r["sign"] > 0 else "google")
        if better == "google":
            g = rf"\textbf{{{g}}}"
        if better == "deepseek":
            d = rf"\textbf{{{d}}}"
        lines.append(f"{r['label']} & {unit} & {'higher' if r['sign'] > 0 else 'lower'} & {g} & {d} & "
                     f"{fmt(r['key'], r['diff'], signed=True)} & "
                     rf"\winbar{{{r['google_wins']}}}{{{r['ties']}}}{{{r['deepseek_wins']}}} \\")
    (GEN / "scorecard_rows.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # --- scenario matrix: one line per scenario
    lines, prev = [], None
    for p in pairs:
        if prev and p["user"] != prev:
            lines.append(r"\addlinespace[3pt]")
        prev = p["user"]
        cells = []
        for key, _, _, _, sign in METRICS:
            a = advantage(p, key, sign)
            cells.append(r"\cd" if a > 0 else r"\cg" if a < 0 else r"\ct")
        dw = sum(advantage(p, k, s) > 0 for k, _, _, _, s in METRICS)
        gw = sum(advantage(p, k, s) < 0 for k, _, _, _, s in METRICS)
        outcome = {"deepseek": r"\textbf{DeepSeek}", "google": r"\textbf{Google}", "tradeoff": r"\textcolor{muted}{neither}"}[dominance(p)]
        user = rf"\id{{{p['user_id']}}}" if p["index"] == 1 else ""
        lines.append(f"{user} & {p['label']} & " + " & ".join(cells) + f" & {gw} & {dw} & {outcome} \\\\")
    (GEN / "scenario_rows.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # --- numbers quoted in the text
    dom = [dominance(p) for p in pairs]
    by = {r["key"]: r for r in rows}
    macros = {
        "NScenarios": len(pairs), "NRuns": 2 * len(pairs),
        "DomDeepseek": dom.count("deepseek"), "DomGoogle": dom.count("google"), "DomTradeoff": dom.count("tradeoff"),
        "NutrDeepseekWins": by["nutrition"]["deepseek_wins"], "DecideDeepseekWins": by["decide_min"]["deepseek_wins"],
        "DecideGoogle": mmss(by["decide_min"]["google"]), "DecideDeepseek": mmss(by["decide_min"]["deepseek"]),
        "NutrGoogle": fmt("nutrition", by["nutrition"]["google"]), "NutrDeepseek": fmt("nutrition", by["nutrition"]["deepseek"]),
        "ShopGoogleWins": by["shop_min"]["google_wins"], "ShopDeepseekWins": by["shop_min"]["deepseek_wins"],
        "PrepGoogleWins": by["prep_min"]["google_wins"], "PrepDeepseekWins": by["prep_min"]["deepseek_wins"],
        "PriceGoogleWins": by["price_usd"]["google_wins"], "PriceDeepseekWins": by["price_usd"]["deepseek_wins"],
        "TasteGoogleWins": by["tastiness"]["google_wins"], "TasteDeepseekWins": by["tastiness"]["deepseek_wins"],
        "TasteTies": by["tastiness"]["ties"],
        "TasteGoogle": fmt("tastiness", by["tastiness"]["google"]), "TasteDeepseek": fmt("tastiness", by["tastiness"]["deepseek"]),
    }
    (GEN / "numbers.tex").write_text(
        "".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in macros.items()), encoding="utf-8")
    return macros


# ---------------------------------------------------------------- figure
def front(points):
    """Non-dominated points when x is minimised and y is maximised, sorted by x."""
    keep = [p for p in points
            if not any((q[0] <= p[0] and q[1] >= p[1]) and (q[0] < p[0] or q[1] > p[1]) for q in points)]
    return sorted(set(keep))


def figure(runs):
    plt.rcParams.update({
        "font.family": "sans-serif", "font.sans-serif": ["Source Sans Pro", "Source Sans 3", "Helvetica Neue", "Arial"],
        "font.size": 8, "axes.edgecolor": MUTED, "axes.linewidth": 0.6, "axes.labelcolor": INK,
        "xtick.color": MUTED, "ytick.color": MUTED, "xtick.labelsize": 7.5, "ytick.labelsize": 7.5,
        "xtick.major.size": 2.5, "ytick.major.size": 0, "xtick.major.width": 0.6, "pdf.fonttype": 42,
    })
    panels = [("decide_min", "Time to decision (min)"), ("price_usd", "Price (US$)"),
              ("prep_min", "Preparation time (min)"), ("nutrition", "Nutritional value (Ofcom)")]
    fig, axes = plt.subplots(1, 4, figsize=(6.5, 2.3), sharey=True)
    for ax, (key, xlabel) in zip(axes, panels):
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
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / "pareto_tradeoffs.pdf")
    fig.savefig(FIG / "pareto_tradeoffs.png", dpi=200)
    plt.close(fig)


def main():
    runs, pairs = load()
    rows = summarise(pairs)

    OUT.mkdir(exist_ok=True)
    with open(OUT / "baselines_clean.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["sheet_row", "user", "scenario", "method"] + [k for k, *_ in METRICS])
        for p in pairs:
            for m in ("google", "deepseek"):
                w.writerow([p[m]["row"], p["user"], p["label"], m] + [round(p[m][k], 3) for k, *_ in METRICS])

    macros = write_tex(pairs, rows)
    figure(runs)

    print(f"{'metric':24}{'Google':>9}{'DeepSeek':>10}{'diff':>8}   Google wins / ties / DeepSeek wins")
    for r in rows:
        print(f"{r['label']:24}{r['google']:9.2f}{r['deepseek']:10.2f}{r['diff']:8.2f}   "
              f"{r['google_wins']:2d} / {r['ties']:2d} / {r['deepseek_wins']:2d}")
    print(f"Pareto, per scenario: DeepSeek dominates {macros['DomDeepseek']}, Google dominates {macros['DomGoogle']}, "
          f"trade-off {macros['DomTradeoff']}")


if __name__ == "__main__":
    main()
