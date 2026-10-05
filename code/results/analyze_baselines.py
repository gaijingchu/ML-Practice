"""First-pass evaluation of the two baselines: scorecard and per-scenario Pareto comparison.

Reads Baselines.xlsx (through load_baselines.py) and writes
    ../../results/scorecard.csv             per metric: means, difference, scenarios won
    ../../results/pareto_by_scenario.csv    per scenario: better baseline on each metric, dominance
    ../../results/RESULTS.md                the same, readable
    ../../results/pareto_tradeoffs.pdf/.png the figure (drawn by plot_tradeoffs.py)
    ../../report/generated/*.tex            table rows and numbers used by the writeup

Usage:
    python analyze_baselines.py
"""
import csv
import statistics as st
from pathlib import Path

from load_baselines import METRICS, load
from plot_tradeoffs import plot_tradeoffs

HERE = Path(__file__).resolve().parent
REPORT = HERE.parents[1] / "report"
GEN, RESULTS = REPORT / "generated", HERE.parents[1] / "results"
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
        user = p["user_id"] if p["index"] == 1 else ""
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


# ---------------------------------------------------------------- result files
def plain(key, x, signed=False):
    """Like fmt(), without LaTeX."""
    return fmt(key, x, signed).replace("$-$", "-").replace("\\%", "%")


def write_results(pairs, rows, macros):
    RESULTS.mkdir(exist_ok=True)
    with open(RESULTS / "scorecard.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["metric", "unit", "better", "google_mean", "deepseek_mean", "difference_deepseek_minus_google",
                    "google_wins", "ties", "deepseek_wins"])
        for r in rows:
            w.writerow([r["label"], r["unit"], "higher" if r["sign"] > 0 else "lower", round(r["google"], 4),
                        round(r["deepseek"], 4), round(r["diff"], 4), r["google_wins"], r["ties"], r["deepseek_wins"]])

    keys = [k for k, *_ in METRICS]
    table = []
    for p in pairs:
        marks = ["D" if advantage(p, k, s) > 0 else "G" if advantage(p, k, s) < 0 else "=" for k, _, _, _, s in METRICS]
        table.append((p, marks, {"deepseek": "DeepSeek", "google": "Google Search", "tradeoff": "neither"}[dominance(p)]))
    with open(RESULTS / "pareto_by_scenario.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["user_id", "anon_id", "scenario", "scenario_text"] + [f"better_{k}" for k in keys]
                   + ["google_wins", "deepseek_wins", "dominates"])
        for p, marks, dom in table:
            w.writerow([p["user_id"], p["user"], p["label"], p["google"]["scenario_text"]] + marks
                       + [marks.count("G"), marks.count("D"), dom])

    L = ["# Baseline evaluation results", "",
         "Generated by `code/results/analyze_baselines.py` from `Baselines.xlsx`. "
         f"{macros['NScenarios']} scenarios, each run with both baselines ({macros['NRuns']} runs). "
         "All metrics are measured offline, on the one recipe the user chose in a run.", "",
         "## Scorecard", "",
         "| Metric | Unit | Better | Google Search (mean) | DeepSeek (mean) | Difference | Google wins | Ties | DeepSeek wins |",
         "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        unit = "min:sec" if r["key"] == "decide_min" else ("share of runs" if r["key"] == "diet_violation" else r["unit"])
        g, d = plain(r["key"], r["google"]), plain(r["key"], r["deepseek"])
        if (r["deepseek"] - r["google"]) * r["sign"] > 0:
            d = f"**{d}**"
        elif (r["deepseek"] - r["google"]) * r["sign"] < 0:
            g = f"**{g}**"
        L.append(f"| {r['label']} | {unit} | {'higher' if r['sign'] > 0 else 'lower'} | {g} | {d} | "
                 f"{plain(r['key'], r['diff'], signed=True)} | {r['google_wins']} | {r['ties']} | {r['deepseek_wins']} |")
    L += ["", "The better mean is in bold. Difference is DeepSeek minus Google. Wins count the scenarios (of 20) in which a "
          "baseline is strictly better; a tie counts for neither.", "",
          "## Pareto comparison", "",
          "For a scenario, one baseline dominates the other if it is at least as good on all seven metrics and strictly "
          "better on at least one.", "",
          f"**DeepSeek dominates in {macros['DomDeepseek']} scenarios, Google Search in {macros['DomGoogle']}, "
          f"and in the other {macros['DomTradeoff']} each baseline wins on some metrics.**", "",
          "| User | Scenario | " + " | ".join(SHORT_HEAD[k] for k in keys) + " | G wins | D wins | Dominates |",
          "|---|---|" + "---|" * (len(keys) + 3)]
    for p, marks, dom in table:
        L.append(f"| {p['user_id']} | {p['label']} | " + " | ".join(marks) + f" | {marks.count('G')} | {marks.count('D')} | "
                 + (f"**{dom}**" if dom != "neither" else dom) + " |")
    L += ["", "G: Google Search is better. D: DeepSeek is better. =: tie. Columns: grocery shopping time, meal preparation "
          "time, price, tastiness, nutritional value, diet violation, time to decision.", "",
          "## Trade-offs", "", "![Tastiness against four costs](pareto_tradeoffs.png)", "",
          "One dot per run. Lower cost and higher tastiness are better, so the ideal corner is the top left of every panel. "
          "The line joins the non-dominated runs of each baseline in that panel. Drawn by `code/results/plot_tradeoffs.py`.", "",
          "## Related files", "",
          "- `scorecard.csv`, `pareto_by_scenario.csv`: the two tables above as data",
          "- `../data/baseline_runs.csv`: every run with all recorded and cleaned values",
          "- `../data/recipes/`: the recipe each run ended with",
          "- `../code/nutrition/output/nutrition_report.md`: how the nutritional value of each recipe was computed", ""]
    (RESULTS / "RESULTS.md").write_text("\n".join(L), encoding="utf-8")


def main():
    runs, pairs = load()
    rows = summarise(pairs)
    macros = write_tex(pairs, rows)
    write_results(pairs, rows, macros)
    plot_tradeoffs(runs)

    print(f"{'metric':24}{'Google':>9}{'DeepSeek':>10}{'diff':>8}   Google wins / ties / DeepSeek wins")
    for r in rows:
        print(f"{r['label']:24}{r['google']:9.2f}{r['deepseek']:10.2f}{r['diff']:8.2f}   "
              f"{r['google_wins']:2d} / {r['ties']:2d} / {r['deepseek_wins']:2d}")
    print(f"Pareto, per scenario: DeepSeek dominates {macros['DomDeepseek']}, Google dominates {macros['DomGoogle']}, "
          f"trade-off {macros['DomTradeoff']}")


if __name__ == "__main__":
    main()
