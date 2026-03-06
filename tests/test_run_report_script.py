import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import run_report


class RunReportScriptTests(unittest.TestCase):
    def test_parse_args(self):
        args = run_report.parse_args(
            [
                "--excel",
                "data.xlsx",
                "--profile",
                "config/profiles/x.yaml",
                "--run-id",
                "r001",
                "--indicators",
                "a,b",
            ]
        )
        self.assertEqual("data.xlsx", args.excel)
        self.assertEqual("config/profiles/x.yaml", args.profile)
        self.assertEqual("r001", args.run_id)
        self.assertEqual("a,b", args.indicators)

    def test_main_calls_generate_report_with_profile_and_manifest(self):
        with patch.object(run_report, "generate_report") as mock_gen:
            mock_gen.main.return_value = {
                "ppt_path": Path("export/runs/r001/ppt/report.pptx"),
                "combined_html_path": Path("export/runs/r001/html/月报汇总浏览.html"),
                "manifest_path": Path("export/runs/r001/manifest.json"),
                "indicator_count": 2,
            }
            result = run_report.main(
                excel_path="data.xlsx",
                profile_path="config/profiles/x.yaml",
                indicators="a,b",
                run_id="r001",
            )

        kwargs = mock_gen.main.call_args.kwargs
        self.assertEqual("data.xlsx", kwargs["excel_path"])
        self.assertEqual("config/profiles/x.yaml", kwargs["profile_path"])
        self.assertEqual(["a", "b"], kwargs["indicator_ids"])
        self.assertTrue(kwargs["emit_manifest"])
        self.assertEqual(
            Path("export/runs/r001/ppt/report.pptx"),
            Path(str(kwargs["output_path"])),
        )
        self.assertEqual(Path("export/runs/r001/ppt/report.pptx"), result["ppt_path"])


if __name__ == "__main__":
    unittest.main()
