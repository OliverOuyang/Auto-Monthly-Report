import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import generate_report


class ErrorHandlingTests(unittest.TestCase):
    def test_main_continue_on_indicator_error(self):
        meta_ok = {
            "indicator_id": "ok1",
            "slide_order": 1,
            "raw_sheet": "raw_ok",
            "chart_title": "ok",
            "report_month": "2026-02",
        }
        meta_bad = {
            "indicator_id": "bad1",
            "slide_order": 2,
            "raw_sheet": "raw_bad",
            "chart_title": "bad",
            "report_month": "2026-02",
        }

        with patch.object(generate_report.excel_reader, "read_meta", return_value=[meta_ok, meta_bad]), \
             patch.object(generate_report.excel_reader, "read_styles", return_value={"colors": {}, "global": {}}), \
             patch.object(generate_report.excel_reader, "read_pivot", return_value=None), \
             patch.object(generate_report.excel_reader, "read_raw", side_effect=["raw_ok", "raw_bad"]), \
             patch.object(generate_report.data_processor, "build_pivot", side_effect=["pivot_ok", ValueError("boom")]), \
             patch.object(generate_report.analyzer, "analyze", return_value=["line"]), \
             patch.object(generate_report.chart_renderer, "render", return_value=Path("chart.png")), \
             patch.object(generate_report.html_generator, "generate", return_value=Path("out.html")), \
             patch.object(generate_report.ppt_generator, "create_presentation", return_value=MagicMock()), \
             patch.object(generate_report.ppt_generator, "add_slide"), \
             patch.object(generate_report.ppt_generator, "save", return_value=Path("out.pptx")):
            result = generate_report.main(excel_path="fake.xlsx", output_path="out.pptx", fail_fast=False)

        self.assertEqual(1, result["success_count"])
        self.assertEqual(1, result["failed_count"])
        self.assertEqual("bad1", result["errors"][0]["indicator_id"])


if __name__ == "__main__":
    unittest.main()

