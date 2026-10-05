# Meal Prep Advisor: baselines code (Team J2IS, 10-718)

| Folder | What it does |
|---|---|
| [`nutrition/`](nutrition/) | Computes the "Nutritional value" metric: the UK Ofcom Nutrient Profiling Model score of every baseline recipe, from USDA food-composition data. See its README for the method and assumptions. |
| [`results/`](results/) | Turns the baselines sheet into the first-pass results of the writeup: the scorecard, the per-scenario Pareto comparison and the trade-off figure. |

```bash
pip install -r nutrition/requirements.txt matplotlib

# nutritional value (writes column K of Baselines.xlsx)
cd nutrition && python compute_nutrition.py && python fill_excel.py && cd ..

# results (writes report/generated/*.tex and report/figures/pareto_tradeoffs.pdf)
cd results && python analyze_baselines.py   # Part 4: scorecard, Pareto table, figure
python export_appendix.py                       # appendices: table of all runs, recipe texts
```

`Baselines.xlsx` is expected two levels above the scripts, next to the `code/` folder.
`results/load_baselines.py` documents how the raw cells are turned into numbers.
