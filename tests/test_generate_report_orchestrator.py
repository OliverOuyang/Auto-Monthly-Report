import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import generate_report


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
            ["--excel", "file.xlsx", "--indicators", "a,b,c", "--output", "x.pptx"]
        )
        self.assertEqual("file.xlsx", args.excel)
        self.assertEqual("a,b,c", args.indicators)
        self.assertEqual("x.pptx", args.output)


if __name__ == "__main__":
    unittest.main()
