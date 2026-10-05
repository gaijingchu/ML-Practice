"""Export the baseline data from the spreadsheet to plain files that can be read on GitHub.

Reads Baselines.xlsx and writes
    ../../data/baseline_runs.csv    one line per run (40): scenario, baseline, recipe, every metric as
                                    recorded and as the number used in the analysis, and the recipe text
    ../../data/recipes/R01_...md    one file per run: the recipe the run ended with, as pasted into the sheet

Run IDs (R1-R40) are the ones used in the writeup: scenarios in sheet order, Google Search then DeepSeek.

Usage:
    python export_data.py
"""
import csv
import re
from pathlib import Path

from analyze_baselines import mmss
from load_baselines import METRICS, load

HERE = Path(__file__).resolve().parent
DATA = HERE.parents[1] / "data"
TITLES = HERE.parent / "nutrition" / "data" / "recipe_titles.csv"
BASELINE = {"google": "Google Search", "deepseek": "DeepSeek (zero-shot, web chat, web search off)"}
RECORDED = {"decide_min": "time_to_decision_recorded", "shop_min": "grocery_shopping_time_recorded",
            "prep_min": "meal_preparation_time_recorded", "price_usd": "price_recorded"}
CLEAN = {"decide_min": "time_to_decision_min", "shop_min": "grocery_shopping_time_min",
         "prep_min": "meal_preparation_time_min", "price_usd": "price_usd", "tastiness": "tastiness_0_to_5",
         "nutrition": "nutritional_value_ofcom_score", "diet_violation": "diet_violation"}


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def main():
    _, pairs = load()
    with open(TITLES, newline="", encoding="utf-8") as fh:
        titles = {int(r["row"]): r["title"] for r in csv.DictReader(fh)}

    recipes_dir = DATA / "recipes"
    recipes_dir.mkdir(parents=True, exist_ok=True)
    for old in recipes_dir.glob("R*.md"):
        old.unlink()

    keys = [k for k, *_ in METRICS]
    header = (["run", "sheet_row", "user_id", "anon_id", "scenario", "baseline", "recipe_title"]
              + [RECORDED[k] for k in RECORDED] + [CLEAN[k] for k in keys] + ["recipe_file", "recipe_text"])
    rows, run_id = [], 0
    for p in pairs:
        for method in ("google", "deepseek"):
            run_id += 1
            r, title = p[method], titles[p[method]["row"]]
            name = f"R{run_id:02d}_{method}_{slug(title)}.md"
            rows.append([f"R{run_id}", r["row"], p["user_id"], p["user"], r["scenario_text"], BASELINE[method].split(" (")[0],
                         title] + [r["recorded"][k] for k in RECORDED] + [round(r[k], 3) for k in keys]
                        + [f"recipes/{name}", r["recipe_text"]])
            (recipes_dir / name).write_text("\n".join([
                f"# R{run_id} · {title}", "",
                f"- **User:** {p['user_id']} ({p['user']})",
                f"- **Scenario:** {r['scenario_text']}",
                f"- **Baseline:** {BASELINE[method]}",
                f"- **Time to decision:** {mmss(r['decide_min'])} (min:sec)",
                f"- **Grocery shopping time:** {r['shop_min']:g} min · **Meal preparation time:** {r['prep_min']:g} min · "
                f"**Price:** ${r['price_usd']:.2f}",
                f"- **Tastiness:** {r['tastiness']:g} / 5 · **Nutritional value (Ofcom score):** {r['nutrition']:g} · "
                f"**Diet violation:** {r['diet_violation']:g}",
                "", "## Recipe", "",
                "As pasted into the sheet from the web page or the chat answer.", "",
                r["recipe_text"], ""]), encoding="utf-8")

    with open(DATA / "baseline_runs.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    print(f"{run_id} runs written to {DATA / 'baseline_runs.csv'} and {recipes_dir}")


if __name__ == "__main__":
    main()
