# -*- coding: utf-8 -*-
"""图表类型注册表 — chart_type 名称 → 渲染函数映射

每个渲染函数签名：
    def renderer(pivot_display, meta, styles, font_prop) -> matplotlib.Figure
"""

import numpy as np
import matplotlib.pyplot as plt


def render_stacked_bar_line(pivot_display, meta, styles, font_prop):
    """堆叠柱状图 + 总计折线。"""
    categories = meta['categories']
    unit = meta.get('unit', '')
    chart_title = meta.get('chart_title', '')
    colors = styles.get('colors', {})
    global_styles = styles.get('global', {})
    line_color = global_styles.get('total_line_color', '#FF0000')
    label_color = global_styles.get('label_color', '#5A5A5A')

    pv = pivot_display
    month_labels = [d.strftime('%b-%y') for d in pv.index]
    n_months = len(month_labels)
    x = np.arange(n_months)
    bw = 0.62

    fig, ax = plt.subplots(figsize=(15, 6))
    fig.patch.set_facecolor('white')

    # ── Stacked bars ──
    bottoms = np.zeros(n_months)
    for cat in categories:
        vals = pv[cat].values.astype(float)
        ax.bar(x, vals, bw, bottom=bottoms, color=colors.get(cat, '#999'),
               label=cat, edgecolor='white', linewidth=0.5, zorder=3)

        # Data labels
        for i, (v, b) in enumerate(zip(vals, bottoms)):
            if v < 0.15:
                continue
            cy = b + v / 2
            if cat == categories[0] and v > 2:
                cy = b + v * 0.25
            lx = x[i] + bw / 2 - 0.04
            ax.text(lx, cy, f'{v:.2f}{unit}', ha='right', va='center',
                    fontsize=10, fontweight='bold', color=label_color,
                    fontproperties=font_prop, zorder=6)

        bottoms += vals

    # ── Total line ──
    if '总计' in pv.columns:
        totals = pv['总计'].values.astype(float)
        ax.plot(x, totals, 'o-', color=line_color, linewidth=2.8, markersize=5,
                markerfacecolor=line_color, markeredgecolor='white',
                markeredgewidth=0.8, zorder=5, label='总计')
        for i, v in enumerate(totals):
            ax.text(x[i], v + 0.25, f'{v:.2f}{unit}', ha='center', va='bottom',
                    fontsize=10, fontweight='bold', color=line_color,
                    fontproperties=font_prop, zorder=6)

    # ── Axis / styling ──
    ax.set_title(chart_title, fontsize=14, fontweight='bold', color='#333',
                 fontproperties=font_prop, pad=18)
    ax.set_xticks(x)
    ax.set_xticklabels(month_labels, fontsize=10, color='#555', fontproperties=font_prop)
    ax.set_xlim(-0.6, n_months - 0.4)
    if '总计' in pv.columns:
        ax.set_ylim(0, max(pv['总计'].values.astype(float)) * 1.12)

    ax.yaxis.set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_color('#CCCCCC')
    ax.tick_params(bottom=True, left=False)

    # ── Legend ──
    handles, labels = ax.get_legend_handles_labels()
    cat_handles = handles[:len(categories)]
    cat_labels = labels[:len(categories)]
    extra_handles = handles[len(categories):]
    extra_labels = labels[len(categories):]
    ax.legend(cat_handles + extra_handles, cat_labels + extra_labels,
              loc='upper center', bbox_to_anchor=(0.5, -0.06),
              ncol=len(categories) + 1, fontsize=10, frameon=False,
              prop=font_prop, handlelength=1.2, handleheight=0.8, columnspacing=2.0)

    plt.tight_layout(rect=[0, 0.04, 1, 1])
    return fig


def render_dual_line(pivot_display, meta, styles, font_prop):
    """双线图（CPS）。"""
    categories = meta['categories']
    chart_title = meta.get('chart_title', '')
    colors = styles.get('colors', {})

    pv = pivot_display
    month_labels = [d.strftime('%b-%y') for d in pv.index]
    n_months = len(month_labels)
    x = np.arange(n_months)

    fig, ax = plt.subplots(figsize=(15, 6))
    fig.patch.set_facecolor('white')

    # ── 两条折线 ──
    for cat in categories:
        vals = pv[cat].values.astype(float)
        color = colors.get(cat, '#4472C4')
        ax.plot(x, vals, 'o-', color=color, linewidth=2.5, markersize=6,
                markerfacecolor=color, markeredgecolor='white',
                markeredgewidth=0.8, zorder=5, label=cat)

        # 数据标签（百分比格式，1位小数）
        for i, v in enumerate(vals):
            ax.text(x[i], v + 0.002, f'{v*100:.1f}%', ha='center', va='bottom',
                    fontsize=10, fontweight='bold', color=color,
                    fontproperties=font_prop, zorder=6)

    # ── Axis / styling ──
    ax.set_title(chart_title, fontsize=14, fontweight='bold', color='#333',
                 fontproperties=font_prop, pad=18)
    ax.set_xticks(x)
    ax.set_xticklabels(month_labels, fontsize=10, color='#555', fontproperties=font_prop)
    ax.set_xlim(-0.4, n_months - 0.6)

    # Y 轴：百分比格式（1位小数）
    ax.yaxis.set_visible(True)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y*100:.1f}%'))
    ax.tick_params(axis='y', labelsize=10, colors='#555')

    # 网格线
    ax.grid(axis='y', color='#DDDDDD', linestyle='-', linewidth=0.5, alpha=0.7, zorder=1)

    # 边框
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color('#CCCCCC')
        spine.set_linewidth(1)

    # ── Legend ──
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.06),
              ncol=len(categories), fontsize=10, frameon=False,
              prop=font_prop, handlelength=1.5, handleheight=0.8, columnspacing=2.0)

    plt.tight_layout(rect=[0, 0.04, 1, 1])
    return fig


def render_bar_multi_line(pivot_display, meta, styles, font_prop):
    """柱状图 + 多折线（双Y轴）。"""
    categories = meta['categories']
    chart_title = meta.get('chart_title', '')
    colors = styles.get('colors', {})

    pv = pivot_display
    month_labels = [d.strftime('%b-%y') for d in pv.index]
    n_months = len(month_labels)
    x = np.arange(n_months)
    bw = 0.5

    fig, ax1 = plt.subplots(figsize=(15, 6))
    fig.patch.set_facecolor('white')

    # ── 左Y轴：柱状图（第一个指标，通常是授信额度） ──
    bar_col = categories[0]
    bar_vals = pv[bar_col].values.astype(float)
    bar_color = colors.get(bar_col, '#FFC000')

    ax1.bar(x, bar_vals, bw, color=bar_color, label=bar_col,
            edgecolor='white', linewidth=0.5, zorder=3)

    # 柱状图数据标签（底部）
    for i, v in enumerate(bar_vals):
        if v > 100:  # 只标注较大的值
            ax1.text(x[i], v * 0.05, f'{v:.0f}', ha='center', va='bottom',
                     fontsize=10, fontweight='bold', color='#555',
                     fontproperties=font_prop, zorder=6)

    ax1.set_ylabel(bar_col, fontsize=10, fontweight='bold', color='#333', fontproperties=font_prop)
    ax1.tick_params(axis='y', labelsize=10, colors='#555')
    ax1.set_ylim(0, max(bar_vals) * 1.15)
    ax1.yaxis.set_visible(True)

    # ── 右Y轴：折线（其余指标，通常是过件率） ──
    ax2 = ax1.twinx()

    line_cats = categories[1:]
    for cat in line_cats:
        vals = pv[cat].values.astype(float)
        color = colors.get(cat, '#4472C4')
        ax2.plot(x, vals, 'o-', color=color, linewidth=2.5, markersize=5,
                 markerfacecolor=color, markeredgecolor='white',
                 markeredgewidth=0.8, zorder=5, label=cat)

        # 数据标签（百分比格式，1位小数，点上方）
        for i, v in enumerate(vals):
            ax2.text(x[i], v + 0.005, f'{v*100:.1f}%', ha='center', va='bottom',
                     fontsize=10, fontweight='bold', color=color,
                     fontproperties=font_prop, zorder=6)

    ax2.set_ylabel('过件率', fontsize=10, fontweight='bold', color='#333', fontproperties=font_prop)
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y*100:.1f}%'))
    ax2.tick_params(axis='y', labelsize=10, colors='#555')

    # ── 共享 X 轴 ──
    ax1.set_title(chart_title, fontsize=14, fontweight='bold', color='#333',
                  fontproperties=font_prop, pad=18)
    ax1.set_xticks(x)
    ax1.set_xticklabels(month_labels, fontsize=10, color='#555', fontproperties=font_prop)
    ax1.set_xlim(-0.6, n_months - 0.4)

    # 网格线（仅左Y轴）
    ax1.grid(axis='y', color='#EEEEEE', linestyle='-', linewidth=0.5, alpha=0.7, zorder=1)

    # 边框
    for spine in ax1.spines.values():
        spine.set_visible(True)
        spine.set_color('#CCCCCC')

    # ── Legend（合并两个轴的图例） ──
    handles1, labels1 = ax1.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(handles1 + handles2, labels1 + labels2,
               loc='upper center', bbox_to_anchor=(0.5, -0.06),
               ncol=len(categories), fontsize=10, frameon=False,
               prop=font_prop, handlelength=1.5, handleheight=0.8, columnspacing=2.0)

    plt.tight_layout(rect=[0, 0.04, 1, 1])
    return fig


# ── 图表类型注册表 ──
CHART_RENDERERS = {
    'stacked_bar_line': render_stacked_bar_line,
    'dual_line': render_dual_line,
    'bar_multi_line': render_bar_multi_line,
}
