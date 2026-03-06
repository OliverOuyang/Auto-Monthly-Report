import unittest

import pandas as pd

from core import preprocess


class PreprocessTests(unittest.TestCase):
    def test_ensure_numeric_and_safe_divide(self):
        df = pd.DataFrame({"a": ["1", "x", None], "b": [2, 0, 4]})
        out = preprocess.ensure_numeric(df, ["a", "b"])
        self.assertEqual([1.0, 0.0, 0.0], out["a"].tolist())

        div = preprocess.safe_divide(out["a"], out["b"])
        self.assertEqual([0.5, 0.0, 0.0], div.tolist())

    def test_apply_filters(self):
        df = pd.DataFrame(
            {"渠道": ["腾讯", "抖音", "API"], "分组": ["A", "B", "A"], "v": [1, 2, 3]}
        )
        out = preprocess.apply_filters(
            df,
            include={"分组": ["A"]},
            exclude={"渠道": ["API"]},
        )
        self.assertEqual(["腾讯"], out["渠道"].tolist())


if __name__ == "__main__":
    unittest.main()

