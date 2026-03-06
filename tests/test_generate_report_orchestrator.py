import unittest
import json
import sys
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import generate_report
from core import data_processor


class GenerateReportOrchestratorTests(unittest.TestCase):
    def test_main_filters_indicator_and_uses_raw_fallback(self):
        meta_keep = {
            "indicator_id": "id_keep",
            "slide_order": 1,
            "raw_sheet": "raw_keep",
            "chart_title": "Keep Chart",
            "report_month": "2026-02",
        }
        meta_skip = {
            "indicator_id": "id_skip",
            "slide_order": 2,
            "raw_sheet": "raw_skip",
            "chart_title": "Skip Chart",
            "report_month": "2026-02",
        }

        with patch.object(generate_report.excel_reader, "read_meta", return_value=[meta_skip, meta_keep]), \
             patch.object(generate_report.excel_reader, "read_styles", return_value={"colors": {}, "global": {}}), \
             patch.object(generate_report.excel_reader, "read_pivot", return_value=None) as read_pivot, \
             patch.object(generate_report.excel_reader, "read_raw", return_value="raw_df") as read_raw, \
             patch.object(generate_report.data_processor, "build_pivot", return_value="pivot_df") as build_pivot, \
             patch.object(generate_report.analyzer, "analyze", return_value=["line1"]), \
             patch.object(generate_report.chart_renderer, "render", return_value=Path("chart.png")) as render_chart, \
             patch.object(generate_report.html_generator, "generate", return_value=Path("out.html")), \
             patch.object(generate_report.ppt_generator, "create_presentation", return_value=MagicMock()) as create_prs, \
             patch.object(generate_report.ppt_generator, "add_slide") as add_slide, \
             patch.object(generate_report.ppt_generator, "save", return_value=Path("out.pptx")) as save_ppt:
            result = generate_report.main(
                excel_path="fake.xlsx",
                indicator_ids=["id_keep"],
                output_path="custom.pptx",
            )

        self.assertEqual(read_pivot.call_count, 1)
        read_pivot.assert_called_once_with("fake.xlsx", "id_keep")
        read_raw.assert_called_once_with("fake.xlsx", "raw_keep")
        build_pivot.assert_called_once_with("raw_df", meta_keep)
        render_chart.assert_called_once()
        add_slide.assert_called_once()
        create_prs.assert_called_once()
        save_ppt.assert_called_once()
        self.assertEqual(Path("out.pptx"), result["ppt_path"])

    def test_parse_args_parses_indicators(self):
        args = generate_report.parse_args(
            [
                "run",
                "--excel",
                "file.xlsx",
                "--indicators",
                "a,b,c",
                "--output",
                "x.pptx",
                "--profile",
                "config/profiles/monthly_report_v1.yaml",
                "--workspace",
                "Data/intermediate/workspaces/run_001",
            ]
        )
        self.assertEqual("run", args.command)
        self.assertEqual("file.xlsx", args.excel)
        self.assertEqual("a,b,c", args.indicators)
        self.assertEqual("x.pptx", args.output)
        self.assertEqual("config/profiles/monthly_report_v1.yaml", args.profile)
        self.assertEqual("Data/intermediate/workspaces/run_001", args.workspace)

    def test_parse_args_backward_compatible_without_explicit_subcommand(self):
        args = generate_report.parse_args(
            [
                "--excel",
                "file.xlsx",
            ]
        )
        self.assertEqual("run", args.command)
        self.assertEqual("file.xlsx", args.excel)

    def test_parse_args_uses_sys_argv_when_not_provided(self):
        with patch.object(sys, "argv", ["generate_report.py", "doctor"]):
            args = generate_report.parse_args()
        self.assertEqual("doctor", args.command)

    def test_main_uses_profile_config_when_profile_path_is_provided(self):
        meta_keep = {
            "indicator_id": "id_keep",
            "slide_order": 1,
            "raw_sheet": "raw_keep",
            "chart_title": "Keep Chart",
            "report_month": "2026-02",
        }
        with patch.object(generate_report.excel_reader, "read_meta_from_profile", return_value=[meta_keep]) as read_meta_profile, \
             patch.object(generate_report.excel_reader, "read_styles_from_profile", return_value={"colors": {}, "global": {}}) as read_styles_profile, \
             patch.object(generate_report.excel_reader, "read_pivot", return_value=None), \
             patch.object(generate_report.excel_reader, "read_raw", return_value="raw_df"), \
             patch.object(generate_report.data_processor, "build_pivot", return_value="pivot_df"), \
             patch.object(generate_report.analyzer, "analyze", return_value=["line1"]), \
             patch.object(generate_report.chart_renderer, "render", return_value=Path("chart.png")), \
             patch.object(generate_report.html_generator, "generate", return_value=Path("out.html")), \
             patch.object(generate_report.ppt_generator, "create_presentation", return_value=MagicMock()), \
             patch.object(generate_report.ppt_generator, "add_slide"), \
             patch.object(generate_report.ppt_generator, "save", return_value=Path("out.pptx")):
            generate_report.main(
                excel_path="fake.xlsx",
                profile_path="config/profiles/monthly_report_v1.yaml",
                output_path="custom.pptx",
            )

        read_meta_profile.assert_called_once_with("config/profiles/monthly_report_v1.yaml")
        read_styles_profile.assert_called_once_with("config/profiles/monthly_report_v1.yaml")

    def test_main_flushes_unpaired_left_chart_as_single_slide(self):
        left_only_meta = {
            "indicator_id": "left_only",
            "slide_order": 1,
            "raw_sheet": "raw_left",
            "chart_title": "Left Chart",
            "report_month": "2026-02",
            "is_left_chart": True,
        }
        with patch.object(generate_report.excel_reader, "read_meta", return_value=[left_only_meta]), \
             patch.object(generate_report.excel_reader, "read_styles", return_value={"colors": {}, "global": {}}), \
             patch.object(generate_report.excel_reader, "read_pivot", return_value=None), \
             patch.object(generate_report.excel_reader, "read_raw", return_value="raw_df"), \
             patch.object(generate_report.data_processor, "build_pivot", return_value="pivot_df"), \
             patch.object(generate_report.analyzer, "analyze", return_value=["line1"]), \
             patch.object(generate_report.chart_renderer, "render", return_value=Path("chart.png")), \
             patch.object(generate_report.html_generator, "generate", return_value=Path("out.html")), \
             patch.object(generate_report.ppt_generator, "create_presentation", return_value=MagicMock()), \
             patch.object(generate_report.ppt_generator, "add_slide") as add_slide, \
             patch.object(generate_report.ppt_generator, "add_dual_chart_slide") as add_dual_slide, \
             patch.object(generate_report.ppt_generator, "save", return_value=Path("out.pptx")):
            generate_report.main(excel_path="fake.xlsx", output_path="out.pptx")

        add_dual_slide.assert_not_called()
        add_slide.assert_called_once()

    def test_v2_full_derived_indicators_have_builder_functions(self):
        # Keep this list aligned with config/profiles/monthly_report_v2_full.yaml derived ids.
        derived_ids = [
            "cps_all_channel",
            "quality_credit",
            "channel_overview_tencent_cost",
            "channel_overview_tencent_quality",
            "channel_overview_douyin_cost",
            "channel_overview_douyin_quality",
            "channel_overview_jingzhun_cost",
            "channel_overview_jingzhun_quality",
            "tencent_request",
            "tencent_win_rate_overall",
            "tencent_win_rate_grouped",
            "tencent_conversion_overall",
            "tencent_conversion_funnel",
            "douyin_request",
            "douyin_win_rate_overall",
            "douyin_win_rate_grouped",
            "douyin_conversion_overall",
            "douyin_conversion_funnel",
            "jingzhun_attack_result",
            "jingzhun_conversion",
        ]

        missing = [
            indicator_id
            for indicator_id in derived_ids
            if getattr(data_processor, f"build_{indicator_id}_pivot", None) is None
        ]
        self.assertEqual([], missing, f"Missing derived builders: {missing}")

    def test_validate_config_reports_missing_derived_builder(self):
        with patch.object(generate_report.excel_reader, "read_meta_from_profile", return_value=[
            {
                "indicator_id": "foo",
                "chart_type": "single_line",
                "data_source_type": "derived",
            }
        ]), patch.object(generate_report.excel_reader, "read_styles_from_profile", return_value={"colors": {}, "global": {}}):
            result = generate_report.validate_config(excel_path="fake.xlsx", profile_path="config/profiles/monthly_report_v1.yaml")
        self.assertFalse(result["ok"])
        self.assertTrue(any("build_foo_pivot" in e for e in result["errors"]))

    def test_main_can_emit_manifest(self):
        meta_keep = {
            "indicator_id": "id_keep",
            "slide_order": 1,
            "raw_sheet": "raw_keep",
            "chart_title": "Keep Chart",
            "report_month": "2026-02",
        }
        base = Path("tests") / ".tmp_manifest"
        (base / "ppt").mkdir(parents=True, exist_ok=True)
        (base / "html").mkdir(parents=True, exist_ok=True)
        output = str(base / "ppt" / "out.pptx")
        with patch.object(generate_report.excel_reader, "read_meta", return_value=[meta_keep]), \
             patch.object(generate_report.excel_reader, "read_styles", return_value={"colors": {}, "global": {}}), \
             patch.object(generate_report.excel_reader, "read_pivot", return_value=None), \
             patch.object(generate_report.excel_reader, "read_raw", return_value="raw_df"), \
             patch.object(generate_report.data_processor, "build_pivot", return_value="pivot_df"), \
             patch.object(generate_report.analyzer, "analyze", return_value=["line1"]), \
             patch.object(generate_report.chart_renderer, "render", return_value=base / "charts" / "chart.png"), \
             patch.object(generate_report.html_generator, "generate", return_value=base / "html" / "out.html"), \
             patch.object(generate_report.ppt_generator, "create_presentation", return_value=MagicMock()), \
             patch.object(generate_report.ppt_generator, "add_slide"), \
             patch.object(generate_report.ppt_generator, "save", return_value=Path(output)):
            result = generate_report.main(
                excel_path="fake.xlsx",
                output_path=output,
                emit_manifest=True,
            )
        manifest_path = Path(result["manifest_path"])
        self.assertTrue(manifest_path.exists())
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(1, data["indicator_count"])
        shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
