"""
run_baseline.py — tests Pranjali's benchmark prompts against the current
Demo-1 pipeline (core.propose) and reports pass/fail per prompt.

Usage:
    1. Copy this file into your argus_demo1/ folder (same level as core.py)
    2. Copy "ARGUS Benchmark.xlsx" into that same folder
    3. pip install openpyxl   (only needed once)
    4. Run:  python run_baseline.py "ARGUS Benchmark.xlsx"
             (optionally: python run_baseline.py "ARGUS Benchmark.xlsx" Benchmark_Prompts
              if the sheet name is ever different from the default)

Requires: Ollama running locally/on the server with the model core.py expects.
No commands are ever executed — propose() only classifies, never runs anything.
"""

import csv
import sys
import time

import openpyxl

from core import propose

DEFAULT_SHEET = "Benchmark_Prompts"


def normalize_risk(raw: str) -> str:
    """Collapse variant labels like 'DESTRUCTIVE (if applicable)' to the base tier."""
    raw = (raw or "").strip().upper()
    for tier in ("SAFE", "REVERSIBLE", "DESTRUCTIVE"):
        if raw.startswith(tier):
            return tier
    return raw  # leave odd ones (e.g. "N/A...") as-is for manual review


def load_rows_from_xlsx(xlsx_path: str, sheet_name: str):
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb[sheet_name] if sheet_name in wb.sheetnames else wb.worksheets[0]

    header_cells = next(ws.iter_rows(min_row=1, max_row=1))
    headers = [str(c.value).strip() if c.value else "" for c in header_cells]

    rows = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0] is None:
            continue
        row_dict = dict(zip(headers, row))
        rows.append(row_dict)
    return rows


def run(xlsx_path: str, sheet_name: str = DEFAULT_SHEET):
    rows = load_rows_from_xlsx(xlsx_path, sheet_name)

    results = []
    correct = 0
    total = 0

    for row in rows:
        prompt = str(row.get("Prompt", "")).strip()
        expected = normalize_risk(row.get("Expected Risk", ""))
        if not prompt:
            continue

        start = time.time()
        try:
            proposal = propose(prompt)
            predicted = proposal["risk_tier"]
            command = proposal["command"]
        except Exception as e:
            predicted = "ERROR"
            command = str(e)
        latency = round(time.time() - start, 2)

        is_pass = (predicted == expected)
        total += 1
        if is_pass:
            correct += 1

        results.append({
            "ID": row.get("ID", ""),
            "Category": row.get("Category", ""),
            "Prompt": prompt,
            "Expected": expected,
            "Predicted": predicted,
            "Pass": is_pass,
            "Command": command,
            "Latency_s": latency,
        })
        print(f"[{row.get('ID','?')}] {'PASS' if is_pass else 'FAIL'}  "
              f"expected={expected:<11} predicted={predicted:<11} '{prompt[:50]}'")

    # write results out
    out_path = "baseline_results.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    print("\n" + "=" * 60)
    print(f"TOTAL: {correct}/{total} correct ({round(100*correct/total, 1)}%)")

    # flag the most important number separately: destructive false negatives
    fn = [r for r in results if r["Expected"] == "DESTRUCTIVE" and r["Predicted"] != "DESTRUCTIVE"]
    print(f"DESTRUCTIVE FALSE NEGATIVES (safety failures): {len(fn)}")
    for r in fn:
        print(f"   [{r['ID']}] predicted {r['Predicted']} instead of DESTRUCTIVE: '{r['Prompt']}'")

    print(f"\nFull results written to {out_path}")


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        print('Usage: python run_baseline.py "ARGUS Benchmark.xlsx" [SheetName]')
        sys.exit(1)
    sheet = sys.argv[2] if len(sys.argv) == 3 else DEFAULT_SHEET
    run(sys.argv[1], sheet)