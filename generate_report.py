# -*- coding: utf-8 -*-
"""Monthly report orchestration entrypoint."""

from __future__ import annotations

import argparse
from pathlib import Path

from core import analyzer, chart_renderer, data_processor, excel_reader, html_generator, ppt_generator


def _resolve_output_dirs(
    excel_path_obj: Path,
    workspace_path: Path | None,
    output_path: str | None,
) -> tuple[Path, Path, Path]:
    if workspace_path:
        root = workspace_path
        return root / "html", root / "ppt", root / "charts"

    if output_path:
        out = Path(output_path)
        if out.parent.name.lower() == "ppt":
            root = out.parent.parent
        else:
            root = out.parent
    else:
        root = excel_path_obj.parent.parent / "export" / "latest"

    return root / "html", root / "ppt", root / "charts"


def _write_combined_html(html_paths: list[Path], out_file: Path) -> Path:
    out_file.parent.mkdir(parents=True, exist_ok=True)
    sections = []
    toc = []
    for idx, p in enumerate(html_paths, start=1):
        rel = p.name
        title = p.stem
        anchor = f"p{idx}"
        toc.append(f'<a href="#{anchor}">{idx:02d}. {title}</a>')
        sections.append(
            f"""
<section id="{anchor}" class="page">
  <h2>{idx:02d}. {title}</h2>
  <iframe src="{rel}" loading="lazy"></iframe>
</section>
""".strip()
        )

    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>月报汇总浏览</title>
  <style>
    body {{ margin: 0; font-family: "Microsoft YaHei", "SimHei", sans-serif; background: #f5f6f8; }}
    .toc {{
      position: sticky; top: 0; z-index: 10; background: #fff; border-bottom: 1px solid #ddd;
      display: flex; gap: 8px; overflow-x: auto; padding: 10px 12px;
    }}
    .toc a {{ color: #333; text-decoration: none; background: #f0f0f0; padding: 6px 10px; border-radius: 6px; white-space: nowrap; }}
    .page {{ width: min(1600px, 96vw); margin: 14px auto; background: #fff; border: 1px solid #e3e3e3; border-radius: 8px; padding: 8px; }}
    .page h2 {{ margin: 6px 8px 10px; font-size: 16px; color: #333; }}
    iframe {{ width: 100%; height: 920px; border: none; background: #fff; }}
  </style>
</head>
<body>
  <nav class="toc">{''.join(toc)}</nav>
  {''.join(sections)}
</body>
</html>
"""
    out_file.write_text(html, encoding="utf-8")
    return out_file


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate monthly report HTML and PPT.")
    parser.add_argument("--excel", required=True, help="Path to the source Excel file.")
    parser.add_argument(
        "--profile",
        default=None,
        help="External YAML profile path. If omitted, read _meta/_styles from Excel.",
    )
    parser.add_argument(
        "--workspace",
        default=None,
        help="Intermediate workspace dir for run artifacts/logs (optional).",
    )
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
    profile_path: str | None = None,
    workspace: str | None = None,
) -> dict:
    excel_path_obj = Path(excel_path)
    workspace_path = Path(workspace) if workspace else None
    export_html_dir, export_ppt_dir, export_chart_dir = _resolve_output_dirs(
        excel_path_obj=excel_path_obj,
        workspace_path=workspace_path,
        output_path=output_path,
    )

    if profile_path:
        meta_list = excel_reader.read_meta_from_profile(profile_path)
        styles = excel_reader.read_styles_from_profile(profile_path)
    else:
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

    # 用于缓存左图信息,以便与右图合并
    pending_left_chart = None

    for i, meta in enumerate(meta_list):
        indicator_id = meta["indicator_id"]
        data_source_type = meta.get("data_source_type", "single")

        if data_source_type == "derived":
            builder_name = f"build_{indicator_id}_pivot"
            builder = getattr(data_processor, builder_name, None)
            if builder is None:
                raise ValueError(f"Derived builder not found: {builder_name}")
            pivot = builder(excel_path, meta)
        else:
            pivot = excel_reader.read_pivot(excel_path, indicator_id)
            if pivot is None:
                raw_sheet = meta.get("raw_sheet")
                if not raw_sheet:
                    raise ValueError(f"Missing raw_sheet for indicator: {indicator_id}")
                raw = excel_reader.read_raw(excel_path, raw_sheet)
                pivot = data_processor.build_pivot(raw, meta)

        lines = analyzer.analyze(pivot, meta)
        chart_path = chart_renderer.render(pivot, meta, styles, export_chart_dir)
        html_path = html_generator.generate(pivot, meta, styles, lines, export_html_dir)

        chart_paths.append(chart_path)
        html_paths.append(html_path)

        # 检查是否需要合并到前一个slide
        is_left_chart = meta.get('is_left_chart', False)
        is_right_chart = meta.get('is_right_chart', False)
        merge_with_prev = meta.get('merge_with_prev', False)

        if is_left_chart:
            # 这是左图,缓存起来等待右图
            pending_left_chart = {
                'meta': meta,
                'chart_path': chart_path,
                'lines': lines
            }
        elif is_right_chart and merge_with_prev and pending_left_chart:
            # 这是右图,且需要合并,使用dual_chart_slide
            ppt_generator.add_dual_chart_slide(
                prs,
                left_meta=pending_left_chart['meta'],
                right_meta=meta,
                styles=styles,
                left_chart_path=pending_left_chart['chart_path'],
                right_chart_path=chart_path,
                lines=pending_left_chart['lines']  # 使用左图的分析文字
            )
            pending_left_chart = None  # 清空缓存
        else:
            # 普通单图slide
            ppt_generator.add_slide(prs, meta, styles, chart_path, lines)
            pending_left_chart = None  # 清空缓存（防止左图后没有右图的情况）

    if pending_left_chart:
        ppt_generator.add_slide(
            prs,
            pending_left_chart["meta"],
            styles,
            pending_left_chart["chart_path"],
            pending_left_chart["lines"],
        )

    if output_path:
        final_ppt = Path(output_path)
    else:
        report_month = str(meta_list[0].get("report_month", "unknown"))
        final_ppt = export_ppt_dir / f"monthly_report_{report_month}.pptx"

    ppt_path = ppt_generator.save(prs, final_ppt)
    combined_html_path = _write_combined_html(html_paths, export_html_dir / "月报汇总浏览.html")
    return {
        "ppt_path": Path(ppt_path),
        "html_paths": html_paths,
        "combined_html_path": combined_html_path,
        "chart_paths": chart_paths,
        "indicator_count": len(meta_list),
        "workspace": workspace_path,
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
        profile_path=args.profile,
        workspace=args.workspace,
    )

    print(f"Generated {result['indicator_count']} indicators.")
    print(f"PPT: {result['ppt_path']}")
    for html_path in result["html_paths"]:
        print(f"HTML: {html_path}")
    print(f"HTML(all): {result['combined_html_path']}")
