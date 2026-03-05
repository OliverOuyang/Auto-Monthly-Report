import unittest
from unittest.mock import patch

import pandas as pd

from core import data_processor


class IndicatorAdjustmentsTests(unittest.TestCase):
    def test_quality_credit_respects_start_month(self):
        df = pd.DataFrame(
            {
                'date_month': ['2024-12-01', '2025-01-01', '2025-02-01'],
                '渠道类别': ['腾讯', '腾讯', '腾讯'],
                'is_age_refuse': ['0', '0', '0'],
                'a_scr': [1, 1, 1],
                't0_ato_num': [100, 100, 100],
                't0_adt_num': [20, 20, 20],
                't0_adt_amt': [20000, 20000, 20000],
            }
        )
        meta = {'report_month': '2025-02', 'start_month': '2025-01'}

        with patch('core.data_processor.pd.read_excel', return_value=df):
            pivot = data_processor.build_quality_credit_pivot('fake.xlsx', meta)

        self.assertListEqual(
            [pd.Timestamp('2025-01-01'), pd.Timestamp('2025-02-01')],
            list(pivot.index),
        )

    def test_tencent_request_daily_volume_divides_by_2(self):
        df = pd.DataFrame(
            {
                'mon': ['2026-02-01', '2026-02-01'],
                'cnt_request': [62_000_000_000, 0],
                'cnt_request_yes': [31_000_000_000, 0],
            }
        )
        meta = {'report_month': '2026-02'}

        with patch('core.data_processor.pd.read_excel', return_value=df):
            pivot = data_processor.build_tencent_request_pivot('fake.xlsx', meta)

        # Feb has 28 days: 62e9/28/1e8/2 = 11.071428...
        self.assertAlmostEqual(11.07142857, float(pivot.iloc[0]['日请求量']), places=6)

    def test_tencent_win_rate_scaled_by_2(self):
        df = pd.DataFrame(
            {
                'mon': ['2026-02-01', '2026-02-01'],
                'v7prea': ['1Q', '2Q'],
                'cnt_request_yes': [100, 300],
                'cnt_exposure': [10, 60],
            }
        )
        meta = {
            'report_month': '2026-02',
            'categories': ['整体竞得率', '1Q竞得率', '2Q竞得率'],
        }

        with patch('core.data_processor.pd.read_excel', return_value=df):
            pivot = data_processor.build_tencent_win_rate_pivot('fake.xlsx', meta)

        self.assertAlmostEqual(0.35, float(pivot.iloc[0]['整体竞得率']), places=8)
        self.assertAlmostEqual(0.20, float(pivot.iloc[0]['1Q竞得率']), places=8)
        self.assertAlmostEqual(0.40, float(pivot.iloc[0]['2Q竞得率']), places=8)


if __name__ == '__main__':
    unittest.main()
