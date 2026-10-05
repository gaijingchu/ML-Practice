# Meal Prep Advisor: baselines code (Team J2IS, 10-718)

| Folder | What it does |
|---|---|
| [`nutrition/`](nutrition/) | Computes the "Nutritional value" metric: the UK Ofcom Nutrient Profiling Model score of every baseline recipe, from USDA food-composition data. See its README for the method and assumptions. |
| [`results/`](results/) | Evaluates the baselines from the sheet. `load_baselines.py` reads and cleans the data; `analyze_baselines.py` computes the scorecard and the per-scenario Pareto comparison; `plot_tradeoffs.py` draws the trade-off figure; `export_data.py` writes the plain-file copy of the data and recipes; `export_appendix.py` writes the writeup's appendices. |

```bash
pip install -r nutrition/requirements.txt matplotlib

# nutritional value (writes column K of Baselines.xlsx)
cd nutrition && python compute_nutrition.py && python fill_excel.py && cd ..

# evaluation (writes ../results/, ../data/, report/generated/ and report/figures/)
cd results
python analyze_baselines.py   # scorecard, Pareto comparison, figure
python plot_tradeoffs.py      # the figure on its own
python export_data.py         # data/baseline_runs.csv and data/recipes/
python export_appendix.py     # appendices of the writeup
```

`Baselines.xlsx` is expected two levels above the scripts, next to the `code/` folder.
`results/load_baselines.py` documents how the raw cells are turned into numbers.
