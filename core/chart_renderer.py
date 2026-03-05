# -*- coding: utf-8 -*-
"""matplotlib 图表渲染 — chart_type 分发"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from pathlib import Path
import pandas as pd

from config.chart_types import CHART_RENDERERS


# 全局字体设置（优先华文楷体，失败时自动回退）
_FONT_CANDIDATES = [
    r'C:\Windows\Fonts\STKAITI.TTF',  # 华文楷体
    r'C:\Windows\Fonts\simkai.ttf',   # 楷体
    r'C:\Windows\Fonts\msyh.ttc',     # 微软雅黑
]
FONT_PATH = next((p for p in _FONT_CANDIDATES if Path(p).exists()), _FONT_CANDIDATES[-1])
FONT_PROP = FontProperties(fname=FONT_PATH)
plt.rcParams['font.sans-serif'] = ['STKaiti', 'KaiTi', 'SimKai', 'Microsoft YaHei', 'SimHei', 'SimSun', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False


def _add_strategy_annotations_to_fig(fig, ax, annotations: list, pivot: pd.DataFrame):
    """
    在matplotlib图表中添加策略标注（红色虚线箭头+文字）。

    Args:
        fig: matplotlib Figure对象
        ax: matplotlib Axes对象（主坐标轴）
        annotations: 策略标注列表 [{'date': 'YYYY-MM-DD', 'label': '标注文字'}, ...]
        pivot: 透视表DataFrame（用于匹配日期索引）
    """
    if not annotations or pivot.empty:
        return

    for anno in annotations:
        anno_date = pd.Timestamp(anno['date'])
        anno_label = anno['label']

        # 找到对应的x轴位置
        try:
            # 查找最接近的月份索引
            date_diffs = [(abs((idx - anno_date).days), i) for i, idx in enumerate(pivot.index)]
            _, closest_idx = min(date_diffs)

            # 添加垂直虚线
            ax.axvline(x=closest_idx, color='#D73027', linestyle='--', linewidth=2, alpha=0.8, zorder=100)

            # 添加箭头和文字标注
            # 获取y轴范围，将标注放在顶部
            ylim = ax.get_ylim()
            y_pos = ylim[1] * 0.95

            # 添加带箭头的文字
            ax.annotate(
                anno_label,
                xy=(closest_idx, y_pos),
                xytext=(closest_idx, y_pos),
                fontproperties=FONT_PROP,
                fontsize=9,
                color='#D73027',
                fontweight='bold',
                ha='center',
                va='top',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='#D73027', alpha=0.9),
                zorder=101
            )

        except (KeyError, ValueError, IndexError):
            # 如果找不到对应的日期，跳过这个标注
            continue


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

    # 添加策略标注（如果存在）
    strategy_annotations = meta.get('strategy_annotations', [])
    if not isinstance(strategy_annotations, list):
        strategy_annotations = []
    if strategy_annotations:
        # 获取主坐标轴
        axes = fig.get_axes()
        if axes:
            main_ax = axes[0]  # 通常第一个是主坐标轴
            _add_strategy_annotations_to_fig(fig, main_ax, strategy_annotations, pivot_display)

    fig.savefig(chart_path, dpi=220, bbox_inches='tight', facecolor='white', pad_inches=0.15)
    plt.close(fig)

    return chart_path
