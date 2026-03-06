# -*- coding: utf-8 -*-
"""One-command runner built on top of generate_report.run flow."""

from __future__ import annotations

import argparse
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import generate_report

DEFAULT_INPUT = r"C:\Users\Oliver\Desktop\数禾工作\16_AI项目\月报自动化\Data\2月月报数据_输入ai_0304_完整.xlsx"
DEFAULT_PROFILE = "config/profiles/monthly_report_v2_full.yaml"
DEFAULT_OUTPUT_ROOT = "export/runs"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run monthly report with standardized output layout.")
    parser.add_argument("--excel", default=DEFAULT_INPUT, help="Source Excel path.")
    parser.add_argument("--profile", default=DEFAULT_PROFILE, help="Profile YAML path.")
    parser.add_argument("--indicators", default=None, help="Comma-separated indicator IDs.")
    parser.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT, help="Run root directory (contains run folders).")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--output", default=None, help="Optional direct PPT output path (overrides output-root/run-id).")
    return parser.parse_args(argv)


def main(
    excel_path: str,
    profile_path: str,
    output_path: str | None = None,
    indicators: str | None = None,
    output_root: str = DEFAULT_OUTPUT_ROOT,
    run_id: str | None = None,
) -> dict:
    if run_id is None:
        run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S")

    indicator_ids = None
    if indicators:
        indicator_ids = [x.strip() for x in indicators.split(",") if x.strip()]

    if output_path:
        final_output = Path(output_path)
    else:
        final_output = Path(output_root) / run_id / "ppt" / "report.pptx"

    result = generate_report.main(
        excel_path=excel_path,
        indicator_ids=indicator_ids,
        output_path=str(final_output),
        profile_path=profile_path,
        workspace=None,
        emit_manifest=True,
    )
    result["run_id"] = run_id
    result["run_root"] = final_output.parent.parent if final_output.parent.name.lower() == "ppt" else final_output.parent
    return result


if __name__ == "__main__":
    args = parse_args()
    result = main(
        excel_path=args.excel,
        profile_path=args.profile,
        output_path=args.output,
        indicators=args.indicators,
        output_root=args.output_root,
        run_id=args.run_id,
    )
    print(f"Run ID: {result['run_id']}")
    print(f"Run Root: {result['run_root']}")
    print(f"PPT: {result['ppt_path']}")
    print(f"HTML(all): {result['combined_html_path']}")
    if result.get("manifest_path"):
        print(f"Manifest: {result['manifest_path']}")
