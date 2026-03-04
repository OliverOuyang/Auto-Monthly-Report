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
                    fontsize=7.5, fontweight='bold', color=label_color,
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
                    fontsize=8.5, fontweight='bold', color=line_color,
                    fontproperties=font_prop, zorder=6)

    # ── Axis / styling ──
    ax.set_title(chart_title, fontsize=14, fontweight='bold', color='#333',
                 fontproperties=font_prop, pad=18)
    ax.set_xticks(x)
    ax.set_xticklabels(month_labels, fontsize=9.5, color='#555', fontproperties=font_prop)
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
              ncol=len(categories) + 1, fontsize=9.5, frameon=False,
              prop=font_prop, handlelength=1.2, handleheight=0.8, columnspacing=2.0)

    plt.tight_layout(rect=[0, 0.04, 1, 1])
    return fig


# ── 图表类型注册表 ──
CHART_RENDERERS = {
    'stacked_bar_line': render_stacked_bar_line,
}
