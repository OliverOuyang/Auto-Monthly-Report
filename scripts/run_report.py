# -*- coding: utf-8 -*-
"""One-command runner: prepare workspace then generate report."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import generate_report
from scripts.prepare_workspace import prepare_workspace

DEFAULT_INPUT = r"C:\Users\Oliver\Desktop\数禾工作\16_AI项目\月报自动化\Data\2月月报数据_大盘ai_0304_新增腾讯.xlsx"
DEFAULT_PROFILE = "config/profiles/monthly_report_v1.yaml"
DEFAULT_OUTPUT = "export/latest/PPT/2月月报_大盘_正式版.pptx"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare workspace and run monthly report.")
    parser.add_argument("--excel", default=DEFAULT_INPUT, help="Source Excel path.")
    parser.add_argument("--profile", default=DEFAULT_PROFILE, help="Profile YAML path.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output PPT path.")
    parser.add_argument("--indicators", default=None, help="Comma-separated indicator IDs.")
    parser.add_argument("--workspace-root", default="Data/intermediate/workspaces")
    parser.add_argument("--run-id", default=None)
    return parser.parse_args(argv)


def main(
    excel_path: str,
    profile_path: str,
    output_path: str,
    indicators: str | None = None,
    workspace_root: str = "Data/intermediate/workspaces",
    run_id: str | None = None,
) -> dict:
    prep = prepare_workspace(
        excel_path=excel_path,
        profile_path=profile_path,
        workspace_root=workspace_root,
        run_id=run_id,
    )
    workspace = Path(prep["workspace"])
    prepared_excel = str(prep["prepared_excel"])

    indicator_ids = None
    if indicators:
        indicator_ids = [x.strip() for x in indicators.split(",") if x.strip()]

    result = generate_report.main(
        excel_path=prepared_excel,
        indicator_ids=indicator_ids,
        output_path=output_path,
        profile_path=None,
        workspace="export/latest",
    )
    result["workspace"] = workspace
    return result


if __name__ == "__main__":
    args = parse_args()
    result = main(
        excel_path=args.excel,
        profile_path=args.profile,
        output_path=args.output,
        indicators=args.indicators,
        workspace_root=args.workspace_root,
        run_id=args.run_id,
    )
    print(f"Workspace: {result['workspace']}")
    print(f"PPT: {result['ppt_path']}")
    for html_path in result["html_paths"]:
        print(f"HTML: {html_path}")
