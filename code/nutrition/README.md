# Nutritional value of the baseline recipes

This folder computes the **"Nutritional value"** column of the baselines sheet: the
**UK Ofcom / FSA Nutrient Profiling Model (NPM 2004-05) score** of each of the 40 recipes
(4 users x 5 scenarios x 2 baselines: Google Search and a zero-shot LLM).

The score is computed per 100 g of the recipe as eaten. **Lower is healthier.** A food that
scores 4 or more is classified "less healthy" by the model.

Results: [`output/nutrition_report.md`](output/nutrition_report.md) (readable),
[`output/nutrition_scores.csv`](output/nutrition_scores.csv) (one line per recipe),
[`output/nutrition_ingredients.csv`](output/nutrition_ingredients.csv) (one line per ingredient).

## Run it

```bash
pip install -r requirements.txt
python test_npm_score.py          # 9 tests, incl. the six worked examples of the official guidance
python build_usda_table.py        # only needed once: downloads USDA data, writes data/usda_*.csv
python compute_nutrition.py       # writes output/
python fill_excel.py              # writes the scores into column K of ../../Baselines.xlsx
```

`data/usda_per100g.csv` and `data/usda_portions.csv` are committed, so `compute_nutrition.py`
runs without the download.

## Files

| File | What it is |
|---|---|
| `npm_score.py` | The model: points tables, the 11-point protein rule, the fruit/veg/nut formula |
| `test_npm_score.py` | Tests: the six worked examples from the guidance, threshold boundaries, the protein rule |
| `build_usda_table.py` | Builds the per-100 g nutrient table from USDA FoodData Central |
| `data/foods.csv` | Each ingredient -> a USDA entry (or a documented custom entry), unit weights, fruit/veg/nut class |
| `data/recipes.csv` | Each recipe as ingredient lines: quantity, unit, ingredient, role, original text, note |
| `data/recipe_titles.csv` | Sheet row -> dish name |
| `compute_nutrition.py` | Weighs every ingredient, sums nutrients, scores, writes the outputs and the report |
| `fill_excel.py` | Writes the scores into the spreadsheet |

## The model

Implemented from the Department of Health's *Nutrient Profiling Technical Guidance* (January 2011),
<https://www.gov.uk/government/publications/the-nutrient-profiling-model>. Per 100 g of food:

- **A points** (0-10 each): energy (kJ), saturated fat (g), total sugars (g), sodium (mg).
- **C points** (0-5 each): fruit, vegetables and nuts (%), fibre (g, AOAC), protein (g).
- **Score = A - C.** If A is 11 or more, protein points count only when fruit/veg/nuts scores 5.
- Fruit, vegetables and nuts % = (FVN + 2 x dried FVN) / (FVN + 2 x dried FVN + other ingredients) x 100.

AOAC fibre thresholds are used because USDA reports AOAC "total dietary fibre".

## Data sources

| Source | Used for |
|---|---|
| USDA FoodData Central, SR Legacy (2018-04) | Most ingredients (raw meat, vegetables, oils, sauces, spices) and household-measure weights |
| USDA FoodData Central, FNDDS 2021-2023 (2024-10) | Foods SR Legacy lacks (cheddar, TVP, agave, coconut oil, hot peppers) |
| USDA FoodData Central, Branded Foods (label data) | Tasty Bite Madras Lentils, Kettle & Fire bone broth, potato gnocchi, Chinese sausage, mirin, sweet bean paste, baby corn, lemon pepper |
| UK CoFID 2021 (McCance & Widdowson) | Creme fraiche, paneer |

Every entry, with its FDC id and per-100 g values, is listed at the end of the report.
Where USDA does not report a nutrient for an entry (20 values across 15 of the 173 ingredients), `foods.csv`
supplies one from the closest USDA entry and says which; the code refuses a fill for a nutrient USDA does report.

## How a recipe becomes ingredient lines

The recipe text in the sheet is free text, so each recipe was read and transcribed by hand into
`data/recipes.csv` (with Claude). Each line keeps the original wording so it can be checked. The rules:

1. **Quantified ingredients are counted as written.** Ranges use the midpoint ("2-3 scallions" -> 2.5).
   "A or B" uses the first option.
2. **Ingredients without a quantity are left out** ("salt to taste", "a pinch", "sesame seeds for garnish",
   "serve with rice"). They are listed per recipe in the report.
3. **Ingredients the recipe marks optional are left out** of the reported score and included in a sensitivity score.
4. **Quantified serving sides are counted** ("To serve: 1/2 cup cooked jasmine rice") and dropped in a sensitivity score.
5. **Water:** water that stays in the dish (soup, gravy, sauce, slurry) is counted; water that is drained off
   (boiling, blanching) or only steams is not.
6. **Dry rice, pasta, noodles and quinoa** are counted at their cooked weight, using the ratio of USDA's
   raw and cooked energy values (for example dry white rice x 2.81), with the nutrient values of the cooked food.
7. **Pulses** count towards fruit/veg/nuts at their hydrated weight. Boiled dal uses USDA's raw/boiled ratio;
   dal that is only soaked (for batters) is assumed to take up its own weight in water.
8. **Fruit, vegetables and nuts** follow the guidance: vegetables, fruit, pulses, nuts, fresh coconut and
   100 % juices count; potatoes, seeds, tofu and TVP do not; dried fruit/vegetables and tomato paste count double.
   Jarred tomato sauce and salsa count 90 %, the ready-made lentil pouch 50 %, ketchup and other condiments 0 %.
9. **Deep-frying oil** that is poured off: 10 % of the raw weight of the fried food is counted as absorbed.
   Egg washes, dredges and marinades are counted in full.
10. **Bone-in chicken:** 68 % of the weight is taken as edible (about a third of a cut-up chicken is bone).

Assumptions that apply to one recipe (the weight of "a bunch", a stand-in ingredient) are in the `note`
column of `recipes.csv` and under "Recipe-specific assumptions" in the report.

## Checks

- `test_npm_score.py` reproduces all six worked examples in the official guidance.
- Where a recipe prints its own nutrition panel, our totals agree closely: Frittata Florentine
  182 vs 176 kcal and 468 vs 451 mg sodium per serving; Pan-Seared Red Snapper 293 vs 288 kcal and
  37.4 vs 36 g protein; Lentils with Chicken and Yogurt Sauce 595 vs 615 kcal and 19.0 vs 19 g fibre.
- The report gives, for each recipe, the score range when every input moves by +/- 10 %, and the score
  under four alternative modelling choices.

## Limitations

- **Evaporation is not modelled.** Total weight is the sum of the ingredients, so long-simmered dishes
  (three-cup chicken, braised pork) are denser in reality than computed, and their true scores are, if
  anything, slightly higher.
- **Unquantified salt is not counted.** 21 of the 40 recipes say "salt to taste" or similar, so sodium is a lower bound.
- **The two baselines write recipes differently.** Google recipes usually say "serve with rice" without a
  quantity (not counted), while LLM recipes often quantify the rice (counted). Rice dilutes sodium and
  saturated fat per 100 g, which favours the LLM recipes. The "without quantified sides" column of the
  report shows the effect.
- **Row 17 (Quinoa Pongal):** the text pasted in the sheet has no quantities. They were taken from the
  source page, <https://www.cookwithkushi.com/quinoa-pongal/>.
- **Rows 38 and 40** say "3 cups dry rice (or 5 cups cooked)". The two are not equivalent
  (3 cups dry is about 9 cups cooked); the first-listed amount is used, as for every other alternative.
- Household measures (a cup of florets, a medium onion, a bunch) are converted with USDA portion weights;
  where USDA has none, the assumed weight is stated in `foods.csv`.
