# Baseline data

Everything here is exported from [`../Baselines.xlsx`](../Baselines.xlsx) by
[`../code/results/export_data.py`](../code/results/export_data.py), so that it can be read without opening the spreadsheet.

- [`baseline_runs.csv`](baseline_runs.csv): one line per run. 40 runs = 20 scenarios x 2 baselines
  (Google Search, zero-shot DeepSeek). Each of the four group members wrote five scenarios and ran both baselines on them.
- [`recipes/`](recipes/): one file per run with the recipe that run ended with, exactly as it was pasted into the sheet
  from the web page (Google Search) or from the chat answer (DeepSeek).

Run IDs `R1`-`R40` are the ones used in the writeup: scenarios in sheet order, Google Search first, then DeepSeek.

## Columns of `baseline_runs.csv`

| Column | Meaning |
|---|---|
| `run`, `sheet_row` | Run ID and the row of the run in the spreadsheet |
| `user_id`, `anon_id` | The group member who ran it (User 1 to User 4), and their anonymous ID in the sheet |
| `scenario` | What the user asked for; used as the search query and as the LLM prompt |
| `baseline` | `Google Search` or `DeepSeek` |
| `recipe_title`, `recipe_file`, `recipe_text` | The recipe the user chose |
| `*_recorded` | The value as typed into the sheet (time to decision as min:sec; one user recorded ranges) |
| `grocery_shopping_time_min`, `meal_preparation_time_min` | LLM estimates, in minutes; a recorded range becomes its midpoint |
| `price_usd` | Price of the ingredients to buy; for ranges, the midpoint of the whole-package cost |
| `tastiness_0_to_5` | The user's rating from the recipe alone (0 inedible ... 5 amazing) |
| `nutritional_value_ofcom_score` | UK Ofcom Nutrient Profiling Model score per 100 g, computed by `code/nutrition` (lower is healthier) |
| `diet_violation` | 1 if the recipe violates the user's diet, else 0 |
| `time_to_decision_min` | Stopwatch time until a recipe was chosen, in minutes |
