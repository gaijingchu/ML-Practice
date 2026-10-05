# Meal Prep Advisor: baselines

Team J2IS (Jeremy, Jingchu, Ignacy, Souraja), 10-718.

This repository holds the baselines assignment: the data we collected, the code that turns it into
results, and the writeup.

| Path | What it is |
|---|---|
| [`report/baselines_writeup.pdf`](report/baselines_writeup.pdf) | The writeup (LaTeX source next to it) |
| [`Baselines.xlsx`](Baselines.xlsx) | The raw data: 40 runs = 20 scenarios x 2 baselines (Google Search, zero-shot DeepSeek), with the recipe each run ended with and seven metrics. The second sheet is the protocol we followed. |
| [`data/`](data/) | The same data as plain files: [`baseline_runs.csv`](data/baseline_runs.csv) (every run, every metric) and [`recipes/`](data/recipes/) (the 40 recipes, one file each) |
| [`results/`](results/) | The evaluation results: [`RESULTS.md`](results/RESULTS.md) (scorecard, per-scenario Pareto comparison, figure), the same tables as CSV, and the figure |
| [`code/results/`](code/results/) | The evaluation code. [`plot_tradeoffs.py`](code/results/plot_tradeoffs.py) draws the figure; `analyze_baselines.py` computes the scorecard and the Pareto comparison; `export_data.py` and `export_appendix.py` write `data/` and the writeup's appendices |
| [`code/nutrition/`](code/nutrition/) | Computes the "Nutritional value" metric: the UK Ofcom Nutrient Profiling Model score of every recipe, from USDA food-composition data. Per-recipe results are in [`code/nutrition/output/`](code/nutrition/output/) |

## Reproduce

```bash
pip install -r code/nutrition/requirements.txt matplotlib

cd code/nutrition
python test_npm_score.py        # the model reproduces the six worked examples of the official guidance
python compute_nutrition.py     # scores all 40 recipes -> output/
python fill_excel.py            # writes the scores into column K of Baselines.xlsx

cd ../results
python analyze_baselines.py     # scorecard, Pareto comparison, figure -> results/, report/generated, report/figures
python plot_tradeoffs.py        # the figure on its own
python export_data.py           # data/baseline_runs.csv and data/recipes/
python export_appendix.py       # the writeup's appendices: all runs, recipe texts

cd ../../report
pdflatex baselines_writeup.tex && pdflatex baselines_writeup.tex
```

The method, data sources and assumptions behind the nutritional value are in
[`code/nutrition/README.md`](code/nutrition/README.md); the full per-recipe results are in
[`code/nutrition/output/nutrition_report.md`](code/nutrition/output/nutrition_report.md).
How the raw spreadsheet cells become numbers is documented at the top of
[`code/results/load_baselines.py`](code/results/load_baselines.py).
