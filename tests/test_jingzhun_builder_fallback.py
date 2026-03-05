import unittest
from unittest.mock import patch

import pandas as pd

from core import data_processor


class JingzhunBuilderFallbackTests(unittest.TestCase):
    def test_attack_result_uses_daily_yi_and_marketing_rate(self):
        df = pd.DataFrame(
            {
                "mon": ["2026-01-01", "2026-02-01"],
                "force_attack_count": [31_000_000_000, 28_000_000_000],
                "allowed_cnt": [6_200_000_000, 5_600_000_000],
            }
        )
        meta = {"report_month": "2026-02"}

        with patch("core.data_processor.pd.read_excel", return_value=df):
            pivot = data_processor.build_jingzhun_attack_result_pivot("fake.xlsx", meta)

        self.assertEqual(["日均撞库量（亿）", "日均可营销量（亿）", "可营销率"], list(pivot.columns))
        self.assertAlmostEqual(10.0, float(pivot.loc[pd.Timestamp("2026-01-01"), "日均撞库量（亿）"]), places=6)
        self.assertAlmostEqual(2.0, float(pivot.loc[pd.Timestamp("2026-01-01"), "日均可营销量（亿）"]), places=6)
        self.assertAlmostEqual(0.2, float(pivot.loc[pd.Timestamp("2026-01-01"), "可营销率"]), places=6)

    def test_conversion_builders_follow_sheet_20_21_definition(self):
        df_jingzhun = pd.DataFrame(
            {
                "mon": ["2026-01-01", "2026-02-01"],
                "allowed_cnt": [4_000_000, 5_000_000],
            }
        )
        df_conv = pd.DataFrame(
            {
                "channel": ["精准营销", "精准营销", "精准营销", "精准营销", "抖音"],
                "mon": ["2026-01-01", "2026-01-01", "2026-02-01", "2026-02-01", "2026-02-01"],
                "login_cnt": [800, 200, 900, 100, 999],
                "t0_adt_cnt": [80, 20, 120, 80, 999],
            }
        )
        meta = {"report_month": "2026-02"}

        def _fake_read_excel(_path, sheet_name=None, **_kwargs):
            if sheet_name == "7_精准":
                return df_jingzhun.copy()
            if sheet_name == "4_转化":
                return df_conv.copy()
            raise AssertionError(f"unexpected sheet_name: {sheet_name}")

        with patch("core.data_processor.pd.read_excel", side_effect=_fake_read_excel):
            all_pivot = data_processor.build_jingzhun_conversion_pivot("fake.xlsx", meta)
            overall = data_processor.build_jingzhun_conversion_overall_pivot("fake.xlsx", meta)
            funnel = data_processor.build_jingzhun_conversion_funnel_pivot("fake.xlsx", meta)

        self.assertEqual(
            ["千次可营销-授信率", "千次可营销-首登率", "首登-授信率"],
            list(all_pivot.columns),
        )
        self.assertEqual(
            ["千次可营销-授信率", "千次可营销-首登率", "首登-授信率"],
            list(overall.columns),
        )
        self.assertEqual(["千次可营销-首登率", "首登-授信率"], list(funnel.columns))

        jan = pd.Timestamp("2026-01-01")
        feb = pd.Timestamp("2026-02-01")
        self.assertAlmostEqual(0.025, float(all_pivot.loc[jan, "千次可营销-授信率"]), places=8)
        self.assertAlmostEqual(0.25, float(all_pivot.loc[jan, "千次可营销-首登率"]), places=8)
        self.assertAlmostEqual(0.1, float(all_pivot.loc[jan, "首登-授信率"]), places=8)
        self.assertAlmostEqual(0.04, float(all_pivot.loc[feb, "千次可营销-授信率"]), places=8)
        self.assertAlmostEqual(0.2, float(all_pivot.loc[feb, "千次可营销-首登率"]), places=8)
        self.assertAlmostEqual(0.2, float(all_pivot.loc[feb, "首登-授信率"]), places=8)


if __name__ == "__main__":
    unittest.main()
