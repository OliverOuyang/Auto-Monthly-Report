# -*- coding: utf-8 -*-
"""matplotlib 图表渲染 — chart_type 分发"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from pathlib import Path

from config.chart_types import CHART_RENDERERS


# 全局字体设置
FONT_PATH = r'C:\Windows\Fonts\msyh.ttc'
FONT_PROP = FontProperties(fname=FONT_PATH)
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False


def render(pivot, meta: dict, styles: dict, output_dir: str | Path) -> Path:
    """
    按 chart_type 渲染图表并保存为 PNG。
    pivot: 已处理的透视表（原始值）
    返回 PNG 文件路径。
    """
    chart_type = meta.get('chart_type', 'stacked_bar_line')
    renderer = CHART_RENDERERS.get(chart_type)
    if renderer is None:
        raise ValueError(f"未注册的图表类型: {chart_type}")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    chart_path = output_dir / f"chart_{meta['indicator_id']}.png"

    unit_divisor = meta.get('unit_divisor', 1)
    pivot_display = pivot / unit_divisor

    fig = renderer(pivot_display, meta, styles, FONT_PROP)
    fig.savefig(chart_path, dpi=220, bbox_inches='tight', facecolor='white', pad_inches=0.15)
    plt.close(fig)

    return chart_path
