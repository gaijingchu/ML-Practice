"""Score every baseline recipe with the UK Ofcom Nutrient Profiling Model.

Inputs (data/):
    usda_per100g.csv    built by build_usda_table.py from USDA FoodData Central
    foods.csv           ingredient key -> USDA entry (or a documented custom entry), unit weights, FVN class
    recipes.csv         one line per ingredient of each recipe (sheet row 3..42), with quantity and unit
    recipe_titles.csv   sheet row -> dish name

Outputs (output/):
    nutrition_scores.csv        one line per recipe: per-100 g nutrients, points, score, sensitivity scores
    nutrition_ingredients.csv   one line per ingredient: grams and nutrient contribution (audit trail)
    nutrition_report.md         the same results as a readable report

Usage:
    python compute_nutrition.py [--xlsx ../../Baselines.xlsx]
The spreadsheet is only read for the user / method / scenario labels.
"""
import argparse
import csv
from collections import defaultdict
from pathlib import Path

from npm_score import fvn_percent, npm_score

HERE = Path(__file__).resolve().parent
DATA, OUT = HERE / "data", HERE / "output"
NUTRIENTS = ["energy_kj", "sat_fat_g", "sugars_g", "sodium_mg", "fibre_g", "protein_g"]
MASS_G = {"g": 1.0, "kg": 1000.0, "oz": 28.3495, "lb": 453.592}
VOLUME_TSP = {"tsp": 1.0, "tbsp": 3.0, "fl_oz": 6.0, "cup": 48.0, "ml": 48.0 / 236.588}
FIRST_ROW, LAST_ROW = 3, 42

# Which ingredient lines each variant counts. "base" is the reported score.
VARIANTS = {
    "base": dict(roles={"main", "side"}, composite=None),
    "with_optional": dict(roles={"main", "side", "optional"}, composite=None),
    "dish_only": dict(roles={"main"}, composite=None),
    "composite_fvn_0": dict(roles={"main", "side"}, composite=0.0),
    "composite_fvn_100": dict(roles={"main", "side"}, composite=1.0),
}


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


# ---------------------------------------------------------------- foods
def load_foods():
    usda = {r["fdc_id"]: r for r in read_csv(DATA / "usda_per100g.csv")}
    foods = {}
    for r in read_csv(DATA / "foods.csv"):
        key = r["key"]
        fills = dict(kv.split("=") for kv in r["fill"].split(";")) if r["fill"] else {}
        if r["fdc_id"]:
            src = usda[r["fdc_id"]]
            per100, filled = {}, []
            for n in NUTRIENTS:
                if src[n] != "":
                    assert n not in fills, f"{key}: {n} is reported by USDA, a fill would override it"
                    per100[n] = float(src[n])
                else:
                    assert n in fills, f"{key}: USDA entry {r['fdc_id']} has no {n} and foods.csv gives no fill"
                    per100[n] = float(fills[n])
                    filled.append(n)
            assert set(fills) == set(filled), f"{key}: unused fill {set(fills) - set(filled)}"
            source = f"USDA {src['source'].replace('_', ' ')} {r['fdc_id']}: {src['description']}"
        else:
            assert not fills, f"{key}: custom entries carry their values directly"
            per100 = {n: float(r[n]) for n in NUTRIENTS}
            source, filled = "custom entry (see note)", []

        mass_factor = 1.0
        if r["dry_fdc_id"]:          # listed dry / uncooked, eaten cooked: convert the weight via the energy ratio
            mass_factor = float(usda[r["dry_fdc_id"]]["energy_kj"]) / per100["energy_kj"]
            assert 1.5 < mass_factor < 4, (key, mass_factor)

        fvn = r["fvn"]
        dried = fvn == "dried"
        share = 0.0 if dried else float(fvn)
        assert 0 <= share <= 1
        units = {u: float(g) for u, g in (kv.split("=") for kv in r["units"].split(";"))} if r["units"] else {}
        foods[key] = dict(per100=per100, units=units, mass_factor=mass_factor, fvn_share=share, dried=dried,
                          composite=0 < share < 1, source=source, filled=filled, note=r["note"])
    return foods


def to_grams(qty, unit, food, key):
    """Weight as eaten, in grams."""
    units = food["units"]
    if unit in MASS_G:
        grams = qty * MASS_G[unit]
    elif unit in units:
        grams = qty * units[unit]
    elif unit in VOLUME_TSP:
        base = next((u for u in ("cup", "tbsp", "tsp") if u in units), None)
        assert base, f"{key}: no volume weight to convert '{unit}'"
        grams = qty * units[base] * VOLUME_TSP[unit] / VOLUME_TSP[base]
    else:
        raise AssertionError(f"{key}: unknown unit '{unit}'")
    return grams * food["mass_factor"]


# ---------------------------------------------------------------- recipes
def load_recipes(foods):
    recipes, excluded = defaultdict(list), defaultdict(list)
    for r in read_csv(DATA / "recipes.csv"):
        row = int(r["row"])
        if r["role"] == "excluded":
            excluded[row].append((r["text"], r["note"]))
            continue
        assert r["role"] in {"main", "side", "optional"}, r
        food = foods[r["food"]]
        grams = to_grams(float(r["qty"]), r["unit"], food, r["food"])
        share, dried = food["fvn_share"], food["dried"]
        if r["fvn"] != "":                       # line-level override (water absorbed by a pulse)
            share, dried = float(r["fvn"]), False
        recipes[row].append(dict(row=row, role=r["role"], food=r["food"], qty=r["qty"], unit=r["unit"], grams=grams,
                                 fvn_share=share, dried=dried, composite=food["composite"] and r["fvn"] == "",
                                 text=r["text"], note=r["note"]))
    assert sorted(recipes) == list(range(FIRST_ROW, LAST_ROW + 1)), "every sheet row needs a recipe"
    return recipes, excluded


def analyse(lines, foods, roles, composite=None):
    total = fvn = dried = other = 0.0
    sums = dict.fromkeys(NUTRIENTS, 0.0)
    for ln in lines:
        if ln["role"] not in roles:
            continue
        g = ln["grams"]
        total += g
        for n in NUTRIENTS:
            sums[n] += foods[ln["food"]]["per100"][n] * g / 100
        if ln["dried"]:
            dried += g
        else:
            share = composite if (composite is not None and ln["composite"]) else ln["fvn_share"]
            fvn += share * g
            other += (1 - share) * g
    per100 = {n: 100 * v / total for n, v in sums.items()}
    pct = fvn_percent(fvn, dried, other)
    res = npm_score(per100["energy_kj"], per100["sat_fat_g"], per100["sugars_g"], per100["sodium_mg"],
                    pct, per100["fibre_g"], per100["protein_g"], fibre_method="AOAC")
    return dict(total_g=total, fvn_pct=pct, per100=per100, res=res)


def score_range(a, rel=0.10):
    """Lowest and highest score when every per-100 g input and the FVN % move by +/- rel."""
    from itertools import product
    p, scores = a["per100"], []
    for signs in product((1 - rel, 1 + rel), repeat=7):
        v = [p[n] * k for n, k in zip(NUTRIENTS, signs)]
        scores.append(npm_score(v[0], v[1], v[2], v[3], min(100.0, a["fvn_pct"] * signs[6]), v[4], v[5]).score)
    return min(scores), max(scores)


# ---------------------------------------------------------------- labels from the spreadsheet
def sheet_labels(xlsx):
    labels = {}
    try:
        import openpyxl
        ws = openpyxl.load_workbook(xlsx, read_only=True)["Main"]
        for i, row in enumerate(ws.iter_rows(min_row=FIRST_ROW, max_row=LAST_ROW, max_col=4, values_only=True), FIRST_ROW):
            method = (row[3] or "").strip()
            labels[i] = dict(user=row[1] or "", method="Google Search" if method.startswith("Google") else "Zero-shot LLM",
                             scenario=(row[2] or "").strip().strip('"“”'))
    except Exception as exc:                      # the scores do not depend on the sheet
        print(f"note: labels not read from {xlsx} ({exc})")
    return labels


# ---------------------------------------------------------------- outputs
def write_outputs(recipes, excluded, foods, labels, titles):
    OUT.mkdir(exist_ok=True)
    results = {row: {v: analyse(lines, foods, **cfg) for v, cfg in VARIANTS.items()} for row, lines in recipes.items()}

    with open(OUT / "nutrition_scores.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["sheet_row", "user", "method", "dish", "total_g",
                    "energy_kj_100g", "sat_fat_g_100g", "sugars_g_100g", "sodium_mg_100g", "fibre_g_100g", "protein_g_100g",
                    "fvn_pct", "pts_energy", "pts_sat_fat", "pts_sugars", "pts_sodium", "A_points",
                    "pts_fvn", "pts_fibre", "pts_protein", "protein_counted", "C_points", "npm_score", "less_healthy"]
                   + [f"npm_score_{v}" for v in VARIANTS if v != "base"] + ["score_min_pm10pct", "score_max_pm10pct"])
        for row in sorted(results):
            b = results[row]["base"]
            p, r, lab = b["per100"], b["res"], labels.get(row, {})
            w.writerow([row, lab.get("user", ""), lab.get("method", ""), titles.get(row, ""), round(b["total_g"], 1),
                        round(p["energy_kj"], 1), round(p["sat_fat_g"], 2), round(p["sugars_g"], 2), round(p["sodium_mg"], 1),
                        round(p["fibre_g"], 2), round(p["protein_g"], 2), round(b["fvn_pct"], 1),
                        r.energy_pts, r.sat_fat_pts, r.sugars_pts, r.sodium_pts, r.a_points,
                        r.fvn_pts, r.fibre_pts, r.protein_pts, int(r.protein_counted), r.c_points, r.score, int(r.less_healthy)]
                       + [results[row][v]["res"].score for v in VARIANTS if v != "base"] + list(score_range(b)))

    with open(OUT / "nutrition_ingredients.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["sheet_row", "role", "recipe_text", "qty", "unit", "food", "grams_as_eaten", "fvn",
                    "energy_kj", "sat_fat_g", "sugars_g", "sodium_mg", "fibre_g", "protein_g", "food_source", "note"])
        for row in sorted(recipes):
            for ln in recipes[row]:
                f = foods[ln["food"]]
                fvn = "dried (x2)" if ln["dried"] else f"{ln['fvn_share']:g}"
                w.writerow([row, ln["role"], ln["text"], ln["qty"], ln["unit"], ln["food"], round(ln["grams"], 1), fvn]
                           + [round(f["per100"][n] * ln["grams"] / 100, 2) for n in NUTRIENTS] + [f["source"], ln["note"]])
            for text, why in excluded[row]:
                w.writerow([row, "excluded", text, "", "", "", "", "", "", "", "", "", "", "", "", why])

    write_report(results, recipes, excluded, foods, labels, titles)
    return results


def write_report(results, recipes, excluded, foods, labels, titles):
    L = []
    add = L.append
    add("# Nutritional value of the baseline recipes: UK Ofcom Nutrient Profiling Model\n")
    add("Generated by `compute_nutrition.py`. Method, sources and assumptions are in `README.md`.\n")
    add("The score is the Ofcom/FSA NPM 2004-05 score per 100 g of the recipe as eaten: **lower is healthier**; "
        "a food scoring **4 or more** is classified \"less healthy\".\n")

    add("## Scores\n")
    add("| Row | User | Method | Dish | kJ | Sat fat g | Sugars g | Sodium mg | Fibre g | Protein g | FVN % | A | C | **Score** | Less healthy |")
    add("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for row in sorted(results):
        b = results[row]["base"]
        p, r, lab = b["per100"], b["res"], labels.get(row, {})
        add(f"| {row} | {lab.get('user', '')} | {lab.get('method', '')} | {titles.get(row, '')} | {p['energy_kj']:.0f} | "
            f"{p['sat_fat_g']:.1f} | {p['sugars_g']:.1f} | {p['sodium_mg']:.0f} | {p['fibre_g']:.1f} | {p['protein_g']:.1f} | "
            f"{b['fvn_pct']:.0f} | {r.a_points} | {r.c_points} | **{r.score}** | {'yes' if r.less_healthy else 'no'} |")
    add("\nNutrient columns are per 100 g. A = points for energy + saturated fat + sugars + sodium; "
        "C = points for fruit/veg/nuts + fibre + protein; score = A - C.\n")

    if labels:
        add("## By baseline\n")
        add("| Method | Recipes | Mean score | Median | Min | Max | Classified less healthy |")
        add("|---|---|---|---|---|---|---|")
        for method in ("Google Search", "Zero-shot LLM"):
            s = sorted(results[row]["base"]["res"].score for row in results if labels[row]["method"] == method)
            n = len(s)
            med = (s[n // 2] + s[(n - 1) // 2]) / 2
            lh = sum(x >= 4 for x in s)
            add(f"| {method} | {n} | {sum(s) / n:.2f} | {med:g} | {s[0]} | {s[-1]} | {lh} of {n} |")
        add("\n| User | Google Search (mean) | Zero-shot LLM (mean) |")
        add("|---|---|---|")
        for user in dict.fromkeys(labels[row]["user"] for row in sorted(results)):
            cells = []
            for method in ("Google Search", "Zero-shot LLM"):
                s = [results[row]["base"]["res"].score for row in results
                     if labels[row]["user"] == user and labels[row]["method"] == method]
                cells.append(f"{sum(s) / len(s):.1f}")
            add(f"| {user} | {cells[0]} | {cells[1]} |")
        add("")

    add("## Points breakdown\n")
    add("| Row | Energy | Sat fat | Sugars | Sodium | FVN | Fibre | Protein | Protein counted | Score |")
    add("|---|---|---|---|---|---|---|---|---|---|")
    for row in sorted(results):
        r = results[row]["base"]["res"]
        add(f"| {row} | {r.energy_pts} | {r.sat_fat_pts} | {r.sugars_pts} | {r.sodium_pts} | {r.fvn_pts} | {r.fibre_pts} | "
            f"{r.protein_pts} | {'yes' if r.protein_counted else 'no'} | {r.score} |")
    add("")

    add("## Sensitivity to the main modelling choices\n")
    add("| Row | Dish | Reported | + optional ingredients | Without quantified sides | Composite sauces 0 % FVN | Composite sauces 100 % FVN |")
    add("|---|---|---|---|---|---|---|")
    changed = defaultdict(int)
    for row in sorted(results):
        v = results[row]
        base = v["base"]["res"].score
        cells = []
        for name in ("with_optional", "dish_only", "composite_fvn_0", "composite_fvn_100"):
            s = v[name]["res"].score
            changed[name] += s != base
            cells.append(f"**{s}**" if s != base else str(s))
        add(f"| {row} | {titles.get(row, '')} | {base} | " + " | ".join(cells) + " |")
    add(f"\nScores that differ from the reported one are in bold. Recipes whose score changes: "
        f"{changed['with_optional']} when optional ingredients are added, {changed['dish_only']} when quantified "
        f"serving sides are dropped, {changed['composite_fvn_0']} / {changed['composite_fvn_100']} when jarred sauces and the "
        f"ready-made lentils count 0 % / 100 % towards fruit, vegetables and nuts.\n")

    add("## How firm each score is\n")
    add("The model works in steps, so a value close to a threshold can move the score. The table gives the lowest and highest "
        "score obtained when every per-100 g nutrient value and the fruit/veg/nut share are moved by 10 % in either direction "
        "(all 128 combinations).\n")
    add("| Row | Dish | Reported | Lowest | Highest | Classification can change |")
    add("|---|---|---|---|---|---|")
    for row in sorted(results):
        b = results[row]["base"]
        lo, hi = score_range(b)
        flips = (lo >= 4) != (hi >= 4)
        add(f"| {row} | {titles.get(row, '')} | {b['res'].score} | {lo} | {hi} | {'yes' if flips else 'no'} |")
    add("")

    add("## Ingredients left out of each recipe\n")
    add("Ingredients without a usable quantity cannot be weighed and are not scored.\n")
    for row in sorted(results):
        opt = [ln["text"] for ln in recipes[row] if ln["role"] == "optional"]
        if not excluded[row] and not opt:
            continue
        add(f"**Row {row} - {titles.get(row, '')}**\n")
        for text, why in excluded[row]:
            add(f"- {text} *({why})*")
        for text in opt:
            add(f"- {text} *(marked optional by the recipe; counted only in the '+ optional' column)*")
        add("")

    add("## Recipe-specific assumptions\n")
    for row in sorted(results):
        notes = list(dict.fromkeys(f"{ln['text']}: {ln['note']}" for ln in recipes[row] if ln["note"]))
        if notes:
            add(f"**Row {row} - {titles.get(row, '')}**\n")
            L.extend(f"- {n}" for n in notes)
            add("")

    used = sorted({ln["food"] for lines in recipes.values() for ln in lines})
    add("## Food composition entries used\n")
    add("| Ingredient key | Source | kJ | Sat fat | Sugars | Sodium mg | Fibre | Protein | FVN | Note |")
    add("|---|---|---|---|---|---|---|---|---|---|")
    for key in used:
        f = foods[key]
        p = f["per100"]
        fvn = "dried x2" if f["dried"] else f"{f['fvn_share']:g}"
        note = f["note"] + (f" [filled: {', '.join(f['filled'])}]" if f["filled"] else "")
        add(f"| {key} | {f['source']} | {p['energy_kj']:g} | {p['sat_fat_g']:g} | {p['sugars_g']:g} | {p['sodium_mg']:g} | "
            f"{p['fibre_g']:g} | {p['protein_g']:g} | {fvn} | {note} |")
    add("\nValues are per 100 g. For ingredients listed dry and eaten cooked (rice, pasta, soba, quinoa) the entry is the "
        "cooked food and the weight is converted with the USDA raw/cooked energy ratio.\n")
    (OUT / "nutrition_report.md").write_text("\n".join(L), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--xlsx", default=str(HERE.parent.parent / "Baselines.xlsx"))
    args = ap.parse_args()

    foods = load_foods()
    recipes, excluded = load_recipes(foods)
    unused = sorted(set(foods) - {ln["food"] for lines in recipes.values() for ln in lines})
    if unused:
        print("foods.csv entries not used by any recipe:", ", ".join(unused))
    titles = {int(r["row"]): r["title"] for r in read_csv(DATA / "recipe_titles.csv")}
    results = write_outputs(recipes, excluded, foods, sheet_labels(args.xlsx), titles)
    for row in sorted(results):
        b = results[row]["base"]
        print(f"row {row:2d}  score {b['res'].score:3d}  (A {b['res'].a_points:2d}, C {b['res'].c_points:2d})  "
              f"{b['total_g']:7.0f} g  {titles.get(row, '')}")
    print(f"wrote {OUT / 'nutrition_scores.csv'}, nutrition_ingredients.csv, nutrition_report.md")


if __name__ == "__main__":
    main()
