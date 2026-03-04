# -*- coding: utf-8 -*-
"""分析文本生成 — 模板注册机制"""

import pandas as pd
from config.analysis_templates import ANALYSIS_TEMPLATES


def analyze(pivot: pd.DataFrame, meta: dict) -> list[str]:
    """
    根据 meta['analysis_template'] 查找模板函数并执行。
    pivot: 已处理的透视表（原始值，非亿）
    返回分析文字列表。
    """
    template_name = meta.get('analysis_template', 'trade_mom')
    func = ANALYSIS_TEMPLATES.get(template_name)
    if func is None:
        return [f"[未找到分析模板: {template_name}]"]

    unit_divisor = meta.get('unit_divisor', 1)
    pivot_display = pivot / unit_divisor
    return func(pivot_display, meta)
