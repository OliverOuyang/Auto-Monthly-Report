import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import task_panel


class TaskPanelTests(unittest.TestCase):
    def test_build_run_request_uses_defaults(self):
        req = task_panel.build_run_request(
            {
                "excel": "Data/x.xlsx",
                "profile": "config/profiles/monthly_report_v2_full.yaml",
                "run_id": "r001",
            }
        )
        self.assertEqual("Data/x.xlsx", req["excel_path"])
        self.assertEqual("config/profiles/monthly_report_v2_full.yaml", req["profile_path"])
        self.assertEqual(["export", "runs", "r001", "ppt", "report.pptx"], list(Path(req["output_path"]).parts[-5:]))
        self.assertTrue(req["emit_manifest"])

    def test_build_run_request_supports_indicators(self):
        req = task_panel.build_run_request(
            {
                "excel": "Data/x.xlsx",
                "profile": "config/profiles/monthly_report_v2_full.yaml",
                "run_id": "r001",
                "indicators": "a,b,c",
            }
        )
        self.assertEqual(["a", "b", "c"], req["indicator_ids"])

    def test_run_request_calls_generate_report(self):
        with patch.object(task_panel, "generate_report") as mock_gen:
            mock_gen.main.return_value = {
                "ppt_path": Path("export/runs/r001/ppt/report.pptx"),
                "combined_html_path": Path("export/runs/r001/html/月报汇总浏览.html"),
                "manifest_path": Path("export/runs/r001/manifest.json"),
                "indicator_count": 23,
            }
            res = task_panel.run_request(
                {
                    "excel": "Data/x.xlsx",
                    "profile": "config/profiles/monthly_report_v2_full.yaml",
                    "run_id": "r001",
                }
            )
        self.assertEqual(23, res["indicator_count"])
        self.assertTrue(str(res["ppt_path"]).endswith("report.pptx"))


if __name__ == "__main__":
    unittest.main()
