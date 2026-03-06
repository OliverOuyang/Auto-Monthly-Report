import unittest
from unittest.mock import patch

import pandas as pd

from core.data_processor import build_cps_all_channel_pivot


class CpsT0FilteringTests(unittest.TestCase):
    def test_t0_cps_denominator_excludes_api_only(self):
        # 分子：业务口径花费（过滤"其他"、"免费渠道"后）
        spend_df = pd.DataFrame(
            {
                "date_month": ["2026-02-01", "2026-02-01", "2026-02-01", "2026-02-01"],
                "渠道类别": ["腾讯", "其他", "免费渠道", "抖音"],
                "业务口径花费": [100.0, 9999.0, 8888.0, 100.0],
            }
        )

        # 手动输入：本用例置零，避免影响校验
        manual_df = pd.DataFrame(
            {
                "input_name": ["促申完花费", "RTA花费"],
                "2026-02": [0.0, 0.0],
            }
        )

        # 1_首借交易：仅用于 1-7全首借CPS，这里给一个常量即可
        trade_df = pd.DataFrame(
            {
                "month": ["2026-02-01"],
                "user_group": ["当月首登M0"],
                "loan_principal_amount": [1000.0],
            }
        )

        # 3_首登到交易转化：T0借款分母
        # 目标口径：仅排除 API，保留 其他/免费渠道
        conversion_df = pd.DataFrame(
            {
                "date_month": ["2026-02-01"] * 4,
                "渠道类别": ["API", "腾讯", "其他", "免费渠道"],
                "a_scr": [1, 1, 1, 1],
                "t0_loa_amt_24h": [100.0, 200.0, 300.0, 500.0],
            }
        )

        meta = {"report_month": "2026-02"}

        def fake_read_excel(_excel_path, sheet_name, *args, **kwargs):
            if sheet_name == "2_花费":
                return spend_df.copy()
            if sheet_name == "_manual_inputs":
                return manual_df.copy()
            if sheet_name == "1_首借交易":
                return trade_df.copy()
            if sheet_name == "3_首登到交易转化":
                return conversion_df.copy()
            raise ValueError(sheet_name)

        with patch("core.data_processor.pd.read_excel", side_effect=fake_read_excel):
            pivot = build_cps_all_channel_pivot("fake.xlsx", meta)

        # 分子=200（腾讯+抖音）
        # 分母（仅排除API）=200+300+500=1000 => T0CPS=0.2
        self.assertAlmostEqual(0.2, float(pivot.loc[pd.Timestamp("2026-02-01"), "1-7 T0CPS"]), places=8)

    def test_cps_all_includes_manual_costs_with_name_variants(self):
        spend_df = pd.DataFrame(
            {
                "date_month": ["2026-02-01"],
                "渠道类别": ["腾讯"],
                "业务口径花费": [100.0],
            }
        )
        # input_name 带空格，模拟真实文件中常见差异
        manual_df = pd.DataFrame(
            {
                "input_name": [" 促申完花费 ", "RTA花费 "],
                "2026-02": [30.0, 20.0],
            }
        )
        trade_df = pd.DataFrame(
            {
                "month": ["2026-02-01"],
                "user_group": ["当月首登M0"],
                "loan_principal_amount": [1000.0],
            }
        )
        conversion_df = pd.DataFrame(
            {
                "date_month": ["2026-02-01"],
                "渠道类别": ["腾讯"],
                "a_scr": [1],
                "t0_loa_amt_24h": [100.0],
            }
        )
        meta = {"report_month": "2026-02"}

        def fake_read_excel(_excel_path, sheet_name, *args, **kwargs):
            if sheet_name == "2_花费":
                return spend_df.copy()
            if sheet_name == "_manual_inputs":
                return manual_df.copy()
            if sheet_name == "1_首借交易":
                return trade_df.copy()
            if sheet_name == "3_首登到交易转化":
                return conversion_df.copy()
            raise ValueError(sheet_name)

        with patch("core.data_processor.pd.read_excel", side_effect=fake_read_excel):
            pivot = build_cps_all_channel_pivot("fake.xlsx", meta)

        # 1-7全首借CPS = (100 + 30 + 20) / 1000 = 0.15
        self.assertAlmostEqual(0.15, float(pivot.loc[pd.Timestamp("2026-02-01"), "1-7全首借CPS"]), places=8)

    def test_cps_all_fallbacks_to_manual_inputs_csv_when_sheet_missing(self):
        spend_df = pd.DataFrame(
            {
                "date_month": ["2026-02-01"],
                "渠道类别": ["腾讯"],
                "业务口径花费": [100.0],
            }
        )
        trade_df = pd.DataFrame(
            {
                "month": ["2026-02-01"],
                "user_group": ["当月首登M0"],
                "loan_principal_amount": [1000.0],
            }
        )
        conversion_df = pd.DataFrame(
            {
                "date_month": ["2026-02-01"],
                "渠道类别": ["腾讯"],
                "a_scr": [1],
                "t0_loa_amt_24h": [100.0],
            }
        )

        csv_df = pd.DataFrame(
            {
                "input_name": ["促申完花费", "RTA花费"],
                "2026-02": [40.0, 10.0],
            }
        )
        meta = {"report_month": "2026-02", "manual_inputs_csv": "manual_inputs.csv"}

        def fake_read_excel(_excel_path, sheet_name, *args, **kwargs):
            if sheet_name == "2_花费":
                return spend_df.copy()
            if sheet_name == "_manual_inputs":
                raise ValueError("_manual_inputs missing")
            if sheet_name == "1_首借交易":
                return trade_df.copy()
            if sheet_name == "3_首登到交易转化":
                return conversion_df.copy()
            raise ValueError(sheet_name)

        with patch("core.data_processor.pd.read_excel", side_effect=fake_read_excel), \
             patch("core.data_processor.pd.read_csv", return_value=csv_df.copy()):
            pivot = build_cps_all_channel_pivot("fake.xlsx", meta)

        # 1-7全首借CPS = (100 + 40 + 10) / 1000 = 0.15
        self.assertAlmostEqual(0.15, float(pivot.loc[pd.Timestamp("2026-02-01"), "1-7全首借CPS"]), places=8)


if __name__ == "__main__":
    unittest.main()
