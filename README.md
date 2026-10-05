# Meal Prep Advisor: baselines

Team J2IS (Jingchu, Jeremy, Ignacy, Souraja), 10-718.

This repository holds the baselines assignment: the data we collected, the code that turns it into
results, and the writeup.

| Path | What it is |
|---|---|
| [`report/baselines_writeup.pdf`](report/baselines_writeup.pdf) | The writeup (LaTeX source next to it) |
| [`Baselines.xlsx`](Baselines.xlsx) | The data: 40 runs = 20 scenarios x 2 baselines (Google Search, zero-shot DeepSeek), with the recipe each run ended with and seven metrics. The second sheet is the protocol we followed. |
| [`code/nutrition/`](code/nutrition/) | Computes the "Nutritional value" metric: the UK Ofcom Nutrient Profiling Model score of every recipe, from USDA food-composition data |
| [`code/results/`](code/results/) | Turns the sheet into the results of the writeup: scorecard, per-scenario Pareto comparison, trade-off figure, appendix tables |

## Reproduce

```bash
pip install -r code/nutrition/requirements.txt matplotlib

cd code/nutrition
python test_npm_score.py        # the model reproduces the six worked examples of the official guidance
python compute_nutrition.py     # scores all 40 recipes -> output/
python fill_excel.py            # writes the scores into column K of Baselines.xlsx

cd ../results
python analyze_baselines.py     # Part 4: tables and figure -> report/generated, report/figures
python export_appendix.py       # appendices: all runs, recipe texts

cd ../../report
pdflatex baselines_writeup.tex && pdflatex baselines_writeup.tex
```

The method, data sources and assumptions behind the nutritional value are in
[`code/nutrition/README.md`](code/nutrition/README.md); the full per-recipe results are in
[`code/nutrition/output/nutrition_report.md`](code/nutrition/output/nutrition_report.md).
How the raw spreadsheet cells become numbers is documented at the top of
[`code/results/load_baselines.py`](code/results/load_baselines.py).
