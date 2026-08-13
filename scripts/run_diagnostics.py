#!/usr/bin/env python3
"""Run temporal CV + fit diagnostics without a full retrain.

Run from repo root:
  uv sync --group forecast
  uv run python scripts/run_diagnostics.py
"""

from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np

from data.forecast.clean import clean_sales, load_clean, load_raw, split_train_test, write_clean
from data.forecast.diagnostics import load_metrics, run_all, write_diagnosis_report
from data.forecast.models_mlforecast import RANDOM_STATE

ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT / "data" / "eval" / "revenue_forecast"


def main() -> None:
    warnings.filterwarnings("ignore", category=FutureWarning)
    np.random.seed(RANDOM_STATE)

    raw_path = ROOT / "data" / "raw" / "healthcore_sales.csv"
    parquet = ROOT / "data" / "process" / "healthcore_sales_clean.parquet"
    if raw_path.exists():
        cleaned = clean_sales(load_raw(raw_path))
        write_clean(cleaned, parquet)
    else:
        cleaned = load_clean(parquet)

    train_df, _test_df = split_train_test(cleaned)
    metrics_path = EVAL_DIR / "metrics.json"
    metrics = load_metrics(metrics_path) if metrics_path.exists() else {}

    print("Running diagnostics on train window", train_df["ds"].min(), "→", train_df["ds"].max())
    diag = run_all(train_df=train_df, metrics=metrics, with_stretch=True)
    report = write_diagnosis_report(diag, metrics)
    print("Wrote", diag["artifacts"]["cv_folds"])
    print("Wrote", diag["artifacts"]["learning_curve"])
    print("Wrote", report)
    print(
        "Fit verdicts:",
        {k: v["verdict"] for k, v in diag["diagnosis"].items()},
    )


if __name__ == "__main__":
    main()
