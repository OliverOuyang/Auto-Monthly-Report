import unittest
from pathlib import Path

from core import excel_reader


class ProfileConfigLoaderTests(unittest.TestCase):
    def test_read_meta_and_styles_from_profile(self):
        profile_content = """
report_month: "2026-02"
manual_inputs_csv: "config/manual_inputs.csv"
indicators:
  - indicator_id: "trade_by_group"
    slide_order: 1
    chart_type: "stacked_bar_line"
    chart_title: "首借交易额-24H"
    raw_sheet: "1_首借交易"
    time_column: "month"
    group_column: "user_group"
    value_column: "loan_principal_amount"
    agg_func: "sum"
    categories: "当月首登M0,存量首登M0"
    filter_exclude: "其他"
    merge_rules: ""
    show_total_line: true
    unit_divisor: 100000000
    unit: "亿"
styles:
  colors:
    当月首登M0: "#4472C4"
  global:
    title_color: "#8B4513"
"""
        td = Path("Data/intermediate/test_tmp_profile_loader")
        td.mkdir(parents=True, exist_ok=True)
        profile = td / "profile.yaml"
        profile.write_text(profile_content, encoding="utf-8")

        meta = excel_reader.read_meta_from_profile(str(profile))
        styles = excel_reader.read_styles_from_profile(str(profile))

        self.assertEqual(1, len(meta))
        self.assertEqual("trade_by_group", meta[0]["indicator_id"])
        self.assertEqual(["当月首登M0", "存量首登M0"], meta[0]["categories"])
        self.assertEqual("config/manual_inputs.csv", meta[0]["manual_inputs_csv"])
        self.assertEqual("#4472C4", styles["colors"]["当月首登M0"])
        self.assertEqual("#8B4513", styles["global"]["title_color"])


if __name__ == "__main__":
    unittest.main()
