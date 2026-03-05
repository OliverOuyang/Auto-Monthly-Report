# -*- coding: utf-8 -*-
"""创建_manual_inputs sheet的临时脚本"""

import pandas as pd
from pathlib import Path

# 读取原Excel
excel_path = Path("Data/2月月报数据_输入ai_0304_完整.xlsx")

# 创建一个简单的_manual_inputs表
manual_inputs = pd.DataFrame({
    'input_name': ['促申完花费', 'RTA花费'],
    '2025-06': [0, 0],
    '2025-07': [0, 0],
    '2025-08': [0, 0],
    '2025-09': [0, 0],
    '2025-10': [0, 0],
    '2025-11': [0, 0],
    '2025-12': [0, 0],
    '2026-01': [0, 0],
    '2026-02': [0, 0],
})

# 读取原Excel的所有sheet
with pd.ExcelFile(excel_path) as xls:
    all_sheets = {}
    for sheet_name in xls.sheet_names:
        all_sheets[sheet_name] = pd.read_excel(xls, sheet_name=sheet_name)

# 添加_manual_inputs
all_sheets['_manual_inputs'] = manual_inputs

# 保存到新文件
output_path = Path("Data/2月月报数据_输入ai_0304_完整_with_manual.xlsx")
with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
    for sheet_name, df in all_sheets.items():
        df.to_excel(writer, sheet_name=sheet_name, index=False)

print(f"Created: {output_path}")
print(f"Added _manual_inputs sheet with {len(manual_inputs)} rows")
