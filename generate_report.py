# -*- coding: utf-8 -*-
"""Monthly report orchestration entrypoint."""

from __future__ import annotations

import argparse
from pathlib import Path

from core import analyzer, chart_renderer, data_processor, excel_reader, html_generator, ppt_generator


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate monthly report HTML and PPT.")
    parser.add_argument("--excel", required=True, help="Path to the structured Excel file.")
    parser.add_argument(
        "--indicators",
        default=None,
        help="Comma-separated indicator IDs to generate. If omitted, generate all.",
    )
    parser.add_argument("--output", default=None, help="Output PPT path. Optional.")
    return parser.parse_args(argv)


def main(
    excel_path: str,
    indicator_ids: list[str] | None = None,
    output_path: str | None = None,
) -> dict:
    excel_path_obj = Path(excel_path)
    export_html_dir = excel_path_obj.parent.parent / "export" / "HTML"
    export_ppt_dir = excel_path_obj.parent.parent / "export" / "PPT"

    meta_list = excel_reader.read_meta(excel_path)
    styles = excel_reader.read_styles(excel_path)

    if indicator_ids:
        wanted = set(indicator_ids)
        meta_list = [m for m in meta_list if m.get("indicator_id") in wanted]

    if not meta_list:
        raise ValueError("No indicators found after filtering.")

    meta_list = sorted(meta_list, key=lambda m: int(m.get("slide_order", 999)))
    prs = ppt_generator.create_presentation()

    html_paths: list[Path] = []
    chart_paths: list[Path] = []

    for meta in meta_list:
        indicator_id = meta["indicator_id"]

        pivot = excel_reader.read_pivot(excel_path, indicator_id)
        if pivot is None:
            raw_sheet = meta.get("raw_sheet")
            if not raw_sheet:
                raise ValueError(f"Missing raw_sheet for indicator: {indicator_id}")
            raw = excel_reader.read_raw(excel_path, raw_sheet)
            pivot = data_processor.build_pivot(raw, meta)

        lines = analyzer.analyze(pivot, meta)
        chart_path = chart_renderer.render(pivot, meta, styles, export_ppt_dir)
        html_path = html_generator.generate(pivot, meta, styles, lines, export_html_dir)
        ppt_generator.add_slide(prs, meta, styles, chart_path, lines)

        chart_paths.append(chart_path)
        html_paths.append(html_path)

    if output_path:
        final_ppt = Path(output_path)
    else:
        report_month = str(meta_list[0].get("report_month", "unknown"))
        final_ppt = export_ppt_dir / f"monthly_report_{report_month}.pptx"

    ppt_path = ppt_generator.save(prs, final_ppt)
    return {
        "ppt_path": Path(ppt_path),
        "html_paths": html_paths,
        "chart_paths": chart_paths,
        "indicator_count": len(meta_list),
    }


if __name__ == "__main__":
    args = parse_args()
    indicators = None
    if args.indicators:
        indicators = [x.strip() for x in args.indicators.split(",") if x.strip()]

    result = main(
        excel_path=args.excel,
        indicator_ids=indicators,
        output_path=args.output,
    )

    print(f"Generated {result['indicator_count']} indicators.")
    print(f"PPT: {result['ppt_path']}")
    for html_path in result["html_paths"]:
        print(f"HTML: {html_path}")
