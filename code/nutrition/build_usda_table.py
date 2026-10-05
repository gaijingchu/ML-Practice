"""Build compact per-100 g nutrient and portion tables from USDA FoodData Central.

Sources (both public domain, https://fdc.nal.usda.gov/download-datasets):
    SR Legacy, release 2018-04        analytical values for basic foods (raw meat, vegetables, oils, spices ...)
    FNDDS 2021-2023, release 2024-10  USDA's survey database: complete nutrient profiles for foods as eaten,
                                      used here for foods SR Legacy lacks or lists with missing nutrients

Outputs (written to data/):
    usda_per100g.csv    one row per food, the nutrients the Ofcom model needs, with a `source` column
    usda_portions.csv   household measures -> gram weights

Usage:
    python build_usda_table.py            # downloads the two zips if they are not cached in data/
"""
import csv
import io
import sys
import urllib.request
import zipfile
from pathlib import Path

BASE = "https://fdc.nal.usda.gov/fdc-datasets/"
RELEASES = {
    "sr_legacy": "FoodData_Central_sr_legacy_food_csv_2018-04.zip",
    "fndds": "FoodData_Central_survey_food_csv_2024-10-31.zip",
}
HERE = Path(__file__).resolve().parent
DATA = HERE / "data"

# FoodData Central nutrient ids -> our column names (all values are per 100 g of food)
NUTRIENTS = {
    1062: "energy_kj",
    1008: "energy_kcal",
    1258: "sat_fat_g",
    2000: "sugars_g",       # total sugars
    1093: "sodium_mg",
    1079: "fibre_g",        # "Fiber, total dietary" (AOAC)
    1003: "protein_g",
    1051: "water_g",
}
EXPECTED_UNITS = {1062: "kJ", 1008: "KCAL", 1258: "G", 2000: "G", 1093: "MG", 1079: "G", 1003: "G", 1051: "G"}
EXPECTED_WORD = {1062: "energy", 1008: "energy", 1258: "saturated", 2000: "sugars", 1093: "sodium",
                 1079: "fiber", 1003: "protein", 1051: "water"}
KCAL_TO_KJ = 4.184
COLS = ["energy_kj", "energy_kcal", "sat_fat_g", "sugars_g", "sodium_mg", "fibre_g", "protein_g", "water_g"]


def read_csv(zf, name):
    member = next(n for n in zf.namelist() if n.endswith("/" + name) or n == name)
    with zf.open(member) as fh:
        yield from csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8"))


def load_release(source, filename):
    cache = DATA / filename
    if not cache.exists():
        print(f"downloading {BASE + filename}")
        req = urllib.request.Request(BASE + filename, headers={"User-Agent": "Mozilla/5.0"})
        cache.write_bytes(urllib.request.urlopen(req, timeout=600).read())
    zf = zipfile.ZipFile(cache)

    # sanity-check the nutrient ids against the release's own nutrient table
    names = {int(r["id"]): (r["name"], r["unit_name"]) for r in read_csv(zf, "nutrient.csv")}
    for nid in NUTRIENTS:
        name, unit = names[nid]
        assert unit == EXPECTED_UNITS[nid] and EXPECTED_WORD[nid] in name.lower(), \
            f"{source}: nutrient {nid} is {name!r} [{unit}], not what this script expects"

    # SR Legacy keys food_nutrient.csv by nutrient id (1008 ...); the FNDDS release keys it by the
    # legacy nutrient number (208 ...). Accept either; the two ranges do not overlap.
    key_to_col = dict(NUTRIENTS)
    for r in read_csv(zf, "nutrient.csv"):
        if int(r["id"]) in NUTRIENTS:
            nbr = int(float(r["nutrient_nbr"]))
            assert nbr < 1000 and nbr not in key_to_col
            key_to_col[nbr] = NUTRIENTS[int(r["id"])]

    foods = {int(r["fdc_id"]): r["description"] for r in read_csv(zf, "food.csv")}
    table = {fid: {} for fid in foods}
    for r in read_csv(zf, "food_nutrient.csv"):
        col = key_to_col.get(int(r["nutrient_id"]))
        if col and r["amount"] != "":
            row = table[int(r["fdc_id"])]
            assert col not in row, f"{source}: duplicate {col} for fdc_id {r['fdc_id']}"
            row[col] = float(r["amount"])
    for row in table.values():
        if "energy_kj" not in row and "energy_kcal" in row:   # FNDDS lists kcal only
            row["energy_kj"] = round(row["energy_kcal"] * KCAL_TO_KJ, 1)

    units = {r["id"]: r["name"] for r in read_csv(zf, "measure_unit.csv")}
    portions = []
    for r in read_csv(zf, "food_portion.csv"):
        fid = int(r["fdc_id"])
        unit = units.get(r["measure_unit_id"], "")
        parts = ["" if unit == "undetermined" else unit, r.get("modifier", ""), r.get("portion_description", "")]
        measure = " ".join(p for p in parts if p and not p.isdigit())
        portions.append([fid, foods.get(fid, ""), r["amount"] or "1", measure, r["gram_weight"]])
    return foods, table, portions


def main():
    DATA.mkdir(exist_ok=True)
    seen = set()
    with open(DATA / "usda_per100g.csv", "w", newline="", encoding="utf-8") as fn, \
         open(DATA / "usda_portions.csv", "w", newline="", encoding="utf-8") as fp:
        wn, wp = csv.writer(fn), csv.writer(fp)
        wn.writerow(["fdc_id", "source", "description"] + COLS)
        wp.writerow(["fdc_id", "description", "amount", "measure", "gram_weight"])
        for source, filename in RELEASES.items():
            foods, table, portions = load_release(source, filename)
            assert not (seen & set(foods)), "fdc_id collision between releases"
            seen |= set(foods)
            for fid in sorted(foods):
                wn.writerow([fid, source, foods[fid]] + [table[fid].get(c, "") for c in COLS])
            wp.writerows(portions)
            print(f"{source}: {len(foods)} foods, {len(portions)} portions")


if __name__ == "__main__":
    sys.exit(main())
