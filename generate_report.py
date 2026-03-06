# -*- coding: utf-8 -*-
"""Monthly report orchestration entrypoint."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
import time
import traceback

from core import analyzer, chart_renderer, data_processor, excel_reader, html_generator, ppt_generator
from core.cache import DiskCache
from core.errors import IndicatorBuildError
from core.logging_utils import log_event, setup_logger
from core.profile_schema import validate_meta_list


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


def _parse_indicator_ids(indicators: str | None) -> list[str] | None:
    if not indicators:
        return None
    out = [x.strip() for x in indicators.split(",") if x.strip()]
    return out or None


def _write_run_manifest(
    root_dir: Path,
    *,
    excel_path: str,
    profile_path: str | None,
    indicator_ids: list[str] | None,
    result: dict,
) -> Path:
    root_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "excel_path": excel_path,
        "profile_path": profile_path,
        "indicator_ids": indicator_ids or [],
        "indicator_count": int(result["indicator_count"]),
        "ppt_path": str(result["ppt_path"]),
        "combined_html_path": str(result["combined_html_path"]),
        "chart_paths": [str(p) for p in result["chart_paths"]],
        "html_paths": [str(p) for p in result["html_paths"]],
        "workspace": str(result["workspace"]) if result.get("workspace") else None,
        "success_count": int(result.get("success_count", 0)),
        "failed_count": int(result.get("failed_count", 0)),
        "errors": result.get("errors", []),
    }
    path = root_dir / "manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _cache_key_for_indicator(excel_path: str, meta: dict) -> str:
    p = Path(excel_path)
    mtime = p.stat().st_mtime if p.exists() else 0
    payload = {
        "excel_path": str(p.resolve()) if p.exists() else excel_path,
        "excel_mtime": mtime,
        "indicator_id": str(meta.get("indicator_id", "")),
        "report_month": str(meta.get("report_month", "")),
        "raw_sheet": str(meta.get("raw_sheet", "")),
        "data_source_type": str(meta.get("data_source_type", "single")),
        "categories": list(meta.get("categories", []) or []),
        "merge_rules": dict(meta.get("merge_rules", {}) or {}),
        "filter_exclude": list(meta.get("filter_exclude", []) or []),
    }
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def validate_config(excel_path: str, profile_path: str | None = None) -> dict:
    errors: list[str] = []
    warnings: list[str] = []

    if profile_path:
        meta_list = excel_reader.read_meta_from_profile(profile_path)
        _ = excel_reader.read_styles_from_profile(profile_path)
    else:
        meta_list = excel_reader.read_meta(excel_path)
        _ = excel_reader.read_styles(excel_path)

    if not meta_list:
        errors.append("No indicators found in config.")
        return {"ok": False, "errors": errors, "warnings": warnings, "indicator_count": 0}

    errors.extend(validate_meta_list(meta_list))
    for idx, meta in enumerate(meta_list, start=1):
        if any(f"Row {idx}:" in e for e in errors):
            continue

        indicator_id = str(meta["indicator_id"])
        if meta.get("data_source_type", "single") == "derived":
            builder_name = f"build_{indicator_id}_pivot"
            if data_processor.get_indicator_builder(indicator_id) is None:
                errors.append(f"Derived builder not found: {builder_name}")

    if profile_path:
        cfg = {}
        try:
            import yaml

            cfg = yaml.safe_load(Path(profile_path).read_text(encoding="utf-8")) or {}
        except Exception as exc:  # pragma: no cover
            warnings.append(f"Could not parse profile for extra checks: {exc}")

        manual_csv = cfg.get("manual_inputs_csv")
        if manual_csv and not Path(manual_csv).exists():
            warnings.append(f"manual_inputs_csv not found: {manual_csv}")

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "indicator_count": len(meta_list),
    }


def doctor() -> dict:
    checks = {}
    for module in ["pandas", "openpyxl", "matplotlib", "pptx", "yaml"]:
        checks[module] = bool(importlib.util.find_spec(module))
    return {"ok": all(checks.values()), "checks": checks}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    args_in = list(sys.argv[1:] if argv is None else argv)
    known = {"run", "validate", "doctor"}
    if not args_in or args_in[0] not in known:
        args_in = ["run", *args_in]

    parser = argparse.ArgumentParser(description="Generate monthly report HTML and PPT.")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Generate report artifacts.")
    run.add_argument("--excel", required=True, help="Path to the source Excel file.")
    run.add_argument(
        "--profile",
        default=None,
        help="External YAML profile path. If omitted, read _meta/_styles from Excel.",
    )
    run.add_argument(
        "--workspace",
        default=None,
        help="Intermediate workspace dir for run artifacts/logs (optional).",
    )
    run.add_argument(
        "--indicators",
        default=None,
        help="Comma-separated indicator IDs to generate. If omitted, generate all.",
    )
    run.add_argument("--output", default=None, help="Output PPT path. Optional.")
    run.add_argument(
        "--emit-manifest",
        action="store_true",
        help="Write run manifest.json to output root.",
    )
    run.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop immediately when one indicator fails.",
    )
    run.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable indicator pivot cache for this run.",
    )

    validate = sub.add_parser("validate", help="Validate profile/meta and builder wiring.")
    validate.add_argument("--excel", required=True, help="Path to the source Excel file.")
    validate.add_argument("--profile", default=None, help="Profile YAML path.")

    sub.add_parser("doctor", help="Check runtime dependencies.")
    return parser.parse_args(args_in)


def _build_pivot_with_fallback(excel_path: str, meta: dict) -> object:
    indicator_id = meta["indicator_id"]
    data_source_type = meta.get("data_source_type", "single")
    if data_source_type == "derived":
        builder_name = f"build_{indicator_id}_pivot"
        builder = data_processor.get_indicator_builder(indicator_id)
        if builder is None:
            raise IndicatorBuildError(f"Derived builder not found: {builder_name}")
        return builder(excel_path, meta)

    pivot = excel_reader.read_pivot(excel_path, indicator_id)
    if pivot is None:
        raw_sheet = meta.get("raw_sheet")
        if not raw_sheet:
            raise IndicatorBuildError(f"Missing raw_sheet for indicator: {indicator_id}")
        raw = excel_reader.read_raw(excel_path, raw_sheet)
        pivot = data_processor.build_pivot(raw, meta)
    return pivot


def main(
    excel_path: str,
    indicator_ids: list[str] | None = None,
    output_path: str | None = None,
    profile_path: str | None = None,
    workspace: str | None = None,
    emit_manifest: bool = False,
    fail_fast: bool = False,
    use_cache: bool = True,
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

    run_root = export_ppt_dir.parent
    if run_root == Path("."):
        run_root = Path("export/latest")
    run_id = run_root.name
    logger = setup_logger(run_root, run_id=run_id)
    cache = DiskCache(run_root.parent / "cache")
    log_event(logger, "run_start", run_id=run_id, message="run started")

    html_paths: list[Path] = []
    chart_paths: list[Path] = []
    error_items: list[dict] = []
    success_count = 0

    pending_left_chart = None
    for idx, meta in enumerate(meta_list):
        indicator_id = str(meta["indicator_id"])
        trace_id = f"{indicator_id}-{idx + 1}"
        started = time.perf_counter()
        log_event(
            logger,
            "indicator_start",
            run_id=run_id,
            indicator_id=indicator_id,
            trace_id=trace_id,
            step="build",
            message=f"building indicator {indicator_id}",
        )

        try:
            cache_key = _cache_key_for_indicator(excel_path, meta)
            if use_cache:
                pivot = cache.get_or_compute(
                    "pivot",
                    cache_key,
                    lambda: _build_pivot_with_fallback(excel_path, meta),
                )
                log_event(
                    logger,
                    "cache_use",
                    run_id=run_id,
                    indicator_id=indicator_id,
                    trace_id=trace_id,
                    step="build",
                    message="used cache lookup for pivot",
                )
            else:
                pivot = _build_pivot_with_fallback(excel_path, meta)

            lines = analyzer.analyze(pivot, meta)
            chart_path = chart_renderer.render(pivot, meta, styles, export_chart_dir)
            html_path = html_generator.generate(pivot, meta, styles, lines, export_html_dir)

            chart_paths.append(chart_path)
            html_paths.append(html_path)

            is_left_chart = meta.get("is_left_chart", False)
            is_right_chart = meta.get("is_right_chart", False)
            merge_with_prev = meta.get("merge_with_prev", False)
            if is_left_chart:
                pending_left_chart = {"meta": meta, "chart_path": chart_path, "lines": lines}
            elif is_right_chart and merge_with_prev and pending_left_chart:
                ppt_generator.add_dual_chart_slide(
                    prs,
                    left_meta=pending_left_chart["meta"],
                    right_meta=meta,
                    styles=styles,
                    left_chart_path=pending_left_chart["chart_path"],
                    right_chart_path=chart_path,
                    lines=pending_left_chart["lines"],
                )
                pending_left_chart = None
            else:
                ppt_generator.add_slide(prs, meta, styles, chart_path, lines)
                pending_left_chart = None

            success_count += 1
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            log_event(
                logger,
                "indicator_success",
                run_id=run_id,
                indicator_id=indicator_id,
                trace_id=trace_id,
                step="done",
                elapsed_ms=elapsed_ms,
                message=f"indicator {indicator_id} done",
            )
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            error_items.append(
                {
                    "indicator_id": indicator_id,
                    "error_type": exc.__class__.__name__,
                    "message": str(exc),
                    "trace_id": trace_id,
                }
            )
            log_event(
                logger,
                "indicator_failed",
                run_id=run_id,
                indicator_id=indicator_id,
                trace_id=trace_id,
                step="failed",
                elapsed_ms=elapsed_ms,
                message=str(exc),
            )
            logger.debug(traceback.format_exc())
            pending_left_chart = None
            if fail_fast:
                raise

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
    result = {
        "ppt_path": Path(ppt_path),
        "html_paths": html_paths,
        "combined_html_path": combined_html_path,
        "chart_paths": chart_paths,
        "indicator_count": len(meta_list),
        "workspace": workspace_path,
        "success_count": success_count,
        "failed_count": len(error_items),
        "errors": error_items,
    }
    if emit_manifest:
        root_dir = Path(ppt_path).parent.parent if Path(ppt_path).parent.name.lower() == "ppt" else Path(ppt_path).parent
        result["manifest_path"] = _write_run_manifest(
            root_dir,
            excel_path=excel_path,
            profile_path=profile_path,
            indicator_ids=indicator_ids,
            result=result,
        )

    log_event(
        logger,
        "run_end",
        run_id=run_id,
        step="done",
        message="run finished",
    )
    return result


if __name__ == "__main__":
    args = parse_args()
    if args.command == "run":
        result = main(
            excel_path=args.excel,
            indicator_ids=_parse_indicator_ids(args.indicators),
            output_path=args.output,
            profile_path=args.profile,
            workspace=args.workspace,
            emit_manifest=args.emit_manifest,
            fail_fast=args.fail_fast,
            use_cache=not args.no_cache,
        )
        print(f"Generated {result['indicator_count']} indicators.")
        print(f"Success: {result['success_count']}, Failed: {result['failed_count']}")
        print(f"PPT: {result['ppt_path']}")
        for html_path in result["html_paths"]:
            print(f"HTML: {html_path}")
        print(f"HTML(all): {result['combined_html_path']}")
        if result.get("manifest_path"):
            print(f"Manifest: {result['manifest_path']}")
        for item in result["errors"]:
            print(f"ERROR[{item['indicator_id']}]: {item['error_type']} {item['message']}")
    elif args.command == "validate":
        report = validate_config(excel_path=args.excel, profile_path=args.profile)
        print(f"OK: {report['ok']}")
        print(f"Indicators: {report['indicator_count']}")
        for w in report["warnings"]:
            print(f"WARN: {w}")
        for e in report["errors"]:
            print(f"ERROR: {e}")
    elif args.command == "doctor":
        report = doctor()
        print(f"OK: {report['ok']}")
        for k, v in report["checks"].items():
            print(f"{k}: {'OK' if v else 'MISSING'}")
