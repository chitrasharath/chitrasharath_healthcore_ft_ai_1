#!/usr/bin/env python3
"""CLI for HealthCore patient incident report analysis."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

from analysis_core import (
    RULE_ORDER,
    RULE_LABELS,
    AnalysisResult,
    analyze,
    load_incidents,
    to_export_rows,
)


def _breakdown_line(label: str, count: int, percentage: float, last: bool = False) -> str:
    prefix = "  └─" if last else "  ├─"
    return f"{prefix} {label:<30} {count:>3}  ({percentage:.1f}%)"


def format_console_report(result: AnalysisResult) -> str:
    """Format analysis result for console output."""
    lines = [
        "=" * 60,
        "  HEALTHCORE — PATIENT INCIDENT REPORT ANALYSIS",
        f"  Source file: {result.source_filename}",
        "=" * 60,
        "",
        f"TOTAL RECORDS IN FILE .......... {result.totals.total}",
        f"  ├─ Valid records ................ {result.totals.valid}",
        f"  └─ Invalid / incomplete .......... {result.totals.invalid}",
        "",
        "INVALID RECORDS BREAKDOWN",
    ]

    invalid_items = [
        (RULE_LABELS[rule], next((i.count for i in result.invalid_breakdown if i.rule == rule), 0))
        for rule in RULE_ORDER
        if any(i.rule == rule for i in result.invalid_breakdown)
    ]

    for index, (label, count) in enumerate(invalid_items):
        prefix = "  └─" if index == len(invalid_items) - 1 else "  ├─"
        dots = "." * max(1, 32 - len(label))
        lines.append(f"{prefix} {label} {dots} {count}")

    for title, items in (
        ("BREAKDOWN BY CATEGORY (valid records)", result.by_category),
        ("BREAKDOWN BY STATUS (valid records)", result.by_status),
        ("BREAKDOWN BY COUNTRY (valid records)", result.by_country),
    ):
        lines.extend(["", title])
        for index, item in enumerate(items):
            pct = item.percentage if item.percentage is not None else 0.0
            lines.append(_breakdown_line(item.label, item.count, pct, index == len(items) - 1))

    lines.extend(
        [
            "",
            "SATISFACTION INDEX (closed cases)",
            f"  Scored cases: {result.satisfaction.scored_cases} of {result.satisfaction.total_closed}",
        ]
    )

    if result.satisfaction.average is not None:
        lines.append(
            f"  Average score: {result.satisfaction.average:.2f} / {result.satisfaction.max_score:.2f}"
        )

    for index, item in enumerate(result.satisfaction.distribution):
        prefix = "  └─" if index == len(result.satisfaction.distribution) - 1 else "  ├─"
        label = f"Score {item.score} ({item.label})"
        dots = "." * max(1, 30 - len(label))
        lines.append(f"{prefix} {label} {dots} {item.count}")

    lines.extend(["", "=" * 60, "Export results to CSV? [y / n]:"])
    return "\n".join(lines)


def write_export_csv(result: AnalysisResult, output_path: Path) -> None:
    """Write export rows to CSV."""
    rows = to_export_rows(result)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["metric", "value", "percentage"])
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "metric": row["metric"],
                    "value": row["value"],
                    "percentage": "" if row["percentage"] is None else row["percentage"],
                }
            )


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python analyze.py <csv_path>", file=sys.stderr)
        return 1

    csv_path = Path(sys.argv[1])
    if not csv_path.is_file():
        print(f"Error: file not found: {csv_path.name}", file=sys.stderr)
        return 1

    try:
        df = load_incidents(csv_path)
        result = analyze(df, csv_path.name)
        print(format_console_report(result))

        answer = input().strip().lower()
        if answer == "y":
            output_path = Path("incident-analysis-export.csv")
            write_export_csv(result, output_path)
            print(f"Exported to {output_path.name}")
    except Exception:
        print("Error: unable to analyze incidents file.", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
