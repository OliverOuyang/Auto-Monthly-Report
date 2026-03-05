# -*- coding: utf-8 -*-
"""Test channel overview builder functions."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.data_processor import build_channel_overview_tencent_pivot

meta = {'report_month': '2026-02'}
excel_path = r'Data/2月月报数据_输入ai_0304_完整.xlsx'

print("Testing Tencent channel overview pivot builder...")
pivot = build_channel_overview_tencent_pivot(excel_path, meta)

# Save to file
output_path = Path("Data/intermediate/test_pivot_tencent.csv")
output_path.parent.mkdir(parents=True, exist_ok=True)
pivot.to_csv(output_path)

print(f"Pivot shape: {pivot.shape}")
print(f"Columns: {list(pivot.columns)}")
print(f"Saved to: {output_path}")
print("\nSummary stats:")
print(pivot.describe().transpose())
