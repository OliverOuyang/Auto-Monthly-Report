# -*- coding: utf-8 -*-
"""Validate new data sheets for P11-21 pages."""

import sys
from pathlib import Path

import pandas as pd


def validate_sheet(excel_path: str, sheet_name: str) -> dict:
    """Validate a single sheet and return statistics."""
    try:
        df = pd.read_excel(excel_path, sheet_name=sheet_name)
    except Exception as e:
        return {
            "sheet_name": sheet_name,
            "status": "ERROR",
            "error": str(e),
        }

    stats = {
        "sheet_name": sheet_name,
        "status": "OK",
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": list(df.columns),
        "null_cells_count": 0,
        "backslash_n_count": 0,
        "sample_data": df.head(3).to_dict(orient="records"),
    }

    # Count \N values and null cells
    for col in df.columns:
        null_count = df[col].isna().sum()
        backslash_n_count = (df[col].astype(str) == r"\N").sum()
        stats["null_cells_count"] += null_count
        stats["backslash_n_count"] += backslash_n_count

    return stats


def main():
    if len(sys.argv) < 2:
        excel_path = "Data/2月月报数据_输入ai_0304_完整.xlsx"
    else:
        excel_path = sys.argv[1]

    sheets_to_validate = [
        "4_转化",      # Source for P11, P15, P19
        "5_腾讯",      # Source for P12-14
        "6_抖音",      # Source for P16-18
        "7_精准",      # Source for P20-21
    ]

    output_lines = [
        "=" * 80,
        f"Data Validation Report for: {excel_path}",
        "=" * 80,
        "",
    ]

    all_stats = []
    for sheet in sheets_to_validate:
        stats = validate_sheet(excel_path, sheet)
        all_stats.append(stats)

        output_lines.append(f"\n### Sheet: {stats['sheet_name']}")
        output_lines.append(f"Status: {stats['status']}")

        if stats["status"] == "ERROR":
            output_lines.append(f"Error: {stats['error']}")
            continue

        output_lines.append(f"Rows: {stats['row_count']}")
        output_lines.append(f"Columns: {stats['column_count']}")
        output_lines.append(f"Column Names: {', '.join(stats['columns'])}")
        output_lines.append(f"Null Cells: {stats['null_cells_count']}")
        output_lines.append(f"\\N Values: {stats['backslash_n_count']}")
        output_lines.append("\nSample Data (first 3 rows):")
        for i, row in enumerate(stats["sample_data"], 1):
            output_lines.append(f"  Row {i}: {row}")

    output_lines.append("\n" + "=" * 80)
    output_lines.append("Summary")
    output_lines.append("=" * 80)

    for stats in all_stats:
        if stats["status"] == "OK":
            output_lines.append(
                f"{stats['sheet_name']}: {stats['row_count']} rows, "
                f"{stats['column_count']} cols, "
                f"{stats['backslash_n_count']} \\N values"
            )
        else:
            output_lines.append(f"{stats['sheet_name']}: ERROR - {stats.get('error', 'Unknown')}")

    report_content = "\n".join(output_lines)
    print(report_content)

    # Save report
    output_dir = Path("Data/intermediate")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "validation_report.txt"
    output_file.write_text(report_content, encoding="utf-8")
    print(f"\nReport saved to: {output_file}")


if __name__ == "__main__":
    main()
