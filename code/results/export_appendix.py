"""Write the appendix material of the writeup: the complete table of runs and the chosen recipes.

Reads Baselines.xlsx and writes
    ../../report/generated/runs_rows.tex    one table line per run (all 40), values as used in the analysis
    ../../report/generated/recipes.tex      the recipe text of every run, as pasted into the sheet

Usage:
    python export_appendix.py
"""
import csv
import re
from pathlib import Path

import openpyxl

from analyze_baselines import mmss
from load_baselines import XLSX, load

HERE = Path(__file__).resolve().parent
GEN = HERE.parents[1] / "report" / "generated"
TITLES = HERE.parent / "nutrition" / "data" / "recipe_titles.csv"
BASELINE = {"google": "Google Search", "deepseek": "DeepSeek"}

# characters pdfLaTeX needs help with
ESCAPES = {"\\": r"\textbackslash{}", "{": r"\{", "}": r"\}", "$": r"\$", "&": r"\&", "#": r"\#", "_": r"\_",
           "%": r"\%", "^": r"\^{}", "~": r"\~{}"}
SYMBOLS = {"▢": r"{\tiny$\square$}", "⅓": r"\smallfrac{1}{3}", "⅛": r"\smallfrac{1}{8}",
           "→": r"$\rightarrow$", "ﬀ": "ff", "º": r"\textdegree{}", " ": " "}


def is_cjk(ch):
    return "一" <= ch <= "鿿"


def encodable(text, codec):
    try:
        text.encode(codec)
        return True
    except UnicodeEncodeError:
        return False


def cjk_runs(run):
    """Split a run of Chinese characters into (font, text) pieces: gbsn covers simplified, bsmi traditional."""
    for font, codec in (("gbsn", "gb2312"), ("bsmi", "big5")):
        if encodable(run, codec):
            return [(font, run)]
    return [("gbsn" if encodable(ch, "gb2312") else "bsmi", ch) for ch in run]


def tex(text):
    """Escape free text for pdfLaTeX."""
    out, i = [], 0
    text = re.sub(r"\s+", " ", text).strip()
    while i < len(text):
        ch = text[i]
        if is_cjk(ch):
            j = i
            while j < len(text) and is_cjk(text[j]):
                j += 1
            out.extend(rf"\zh{{{font}}}{{{piece}}}" for font, piece in cjk_runs(text[i:j]))
            i = j
            continue
        out.append(ESCAPES.get(ch) or SYMBOLS.get(ch) or ch)
        i += 1
    return "".join(out)


def num(x, decimals=None):
    if decimals is not None:
        return f"{x:.{decimals}f}"
    return f"{x:g}"


def main():
    _, pairs = load()
    with open(TITLES, newline="", encoding="utf-8") as fh:
        titles = {int(r["row"]): r["title"] for r in csv.DictReader(fh)}
    ws = openpyxl.load_workbook(XLSX)["Main"]
    GEN.mkdir(parents=True, exist_ok=True)

    rows, recipes, run_id, prev_user = [], [], 0, None
    for p in pairs:
        if p["user"] != prev_user:
            if prev_user is not None:
                rows.append(r"\addlinespace[2pt]")
            rows.append(rf"\rowcolor{{tint}}\multicolumn{{11}}{{@{{}}l}}{{\hd{{\id{{{p['user_id']}}} ({p['user']})}}}} \\")
            prev_user = p["user"]
        for method in ("google", "deepseek"):
            run_id += 1
            r = p[method]
            title = titles[r["row"]]
            scenario = tex(p["label"]) if method == "google" else ""
            rows.append(
                f"R{run_id} & {scenario} & \\key{{{method}}}{{{BASELINE[method].split()[0]}}} & {tex(title)} & "
                f"{num(r['shop_min'])} & {num(r['prep_min'])} & {num(r['price_usd'], 2)} & {num(r['tastiness'])} & "
                f"{num(r['nutrition']).replace('-', '$-$')} & {num(r['diet_violation'])} & {mmss(r['decide_min'])} \\\\")
            recipes.append(
                rf"\recipe{{R{run_id}}}{{{tex(title)}}}{{{p['user_id']} \textperiodcentered{{}} {tex(p['label'])} "
                rf"\textperiodcentered{{}} {BASELINE[method]}}}" + "\n" + tex(ws.cell(r["row"], 5).value) + "\n\\par\n")
        rows.append(r"\addlinespace[1.5pt]")
    (GEN / "runs_rows.tex").write_text("\n".join(rows) + "\n", encoding="utf-8")
    (GEN / "recipes.tex").write_text("\n".join(recipes), encoding="utf-8")
    print(f"{run_id} runs written to {GEN / 'runs_rows.tex'} and recipes.tex")


if __name__ == "__main__":
    main()
