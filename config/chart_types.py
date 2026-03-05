# -*- coding: utf-8 -*-
"""图表类型注册表 — chart_type 名称 → 渲染函数映射

每个渲染函数签名：
    def renderer(pivot_display, meta, styles, font_prop) -> matplotlib.Figure
"""

import numpy as np
import matplotlib.pyplot as plt


def _is_dual_chart(meta: dict) -> bool:
    return bool(meta.get('is_left_chart', False) or meta.get('is_right_chart', False))


def _figsize(meta: dict) -> tuple[float, float]:
    # 并排图：适当收窄宽度并增加高度，提升页面填充感
    return (8.3, 6.9) if _is_dual_chart(meta) else (15, 6)


def _pct_decimals(label: str) -> int:
    return 2 if '竞得率' in str(label) else 1


def _fmt_pct(v: float, label: str) -> str:
    return f'{v * 100:.{_pct_decimals(label)}f}%'


def _fmt_value(v: float, label: str) -> str:
    label_text = str(label)
    if 'CVR' in label_text:
        return f'{v:.4f}'
    if abs(v) < 1:
        return _fmt_pct(v, label_text)
    return f'{v:.0f}'


def _label_offset(vals: np.ndarray) -> float:
    vmax = float(np.nanmax(vals)) if len(vals) else 0.0
    vmin = float(np.nanmin(vals)) if len(vals) else 0.0
    span = max(vmax - vmin, abs(vmax), 1e-6)
    return span * 0.03


def _set_embedded_chart_title(ax, meta: dict, font_prop) -> None:
    if not _is_dual_chart(meta):
        return
    title = str(meta.get('chart_title', '')).strip()
    if not title:
        return
    ax.set_title(
        title,
        fontsize=12,
        fontweight='bold',
        color='#333333',
        fontproperties=font_prop,
        pad=8,
        loc='center',
    )


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

    fig, ax = plt.subplots(figsize=_figsize(meta))
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
            ax.text(lx, cy, f'{v:.1f}{unit}', ha='right', va='center',
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
            ax.text(x[i], v + 0.25, f'{v:.1f}{unit}', ha='center', va='bottom',
                    fontsize=8.5, fontweight='bold', color=line_color,
                    fontproperties=font_prop, zorder=6)

    # ── Axis / styling ──
    # ax.set_title(chart_title, fontsize=14, fontweight='bold', color='#333',
    #              fontproperties=font_prop, pad=18)  # 删除标题
    ax.set_xticks(x)
    ax.set_xticklabels(month_labels, fontsize=9.5, color='#555', fontproperties=font_prop)
    ax.set_xlim(-0.6, n_months - 0.4)
    if '总计' in pv.columns:
        ax.set_ylim(0, max(pv['总计'].values.astype(float)) * 1.12)

    ax.yaxis.set_visible(False)
    ax.grid(False)  # 去掉网格线
    for spine in ax.spines.values():
        spine.set_visible(False)  # 去掉所有边框
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


def render_dual_line(pivot_display, meta, styles, font_prop):
    """双线图（双Y轴版本，适用于数量级差异大的两个指标，如CTR和CVR）。"""
    categories = meta['categories']
    chart_title = meta.get('chart_title', '')
    colors = styles.get('colors', {})

    figsize = _figsize(meta)

    pv = pivot_display
    month_labels = [d.strftime('%b-%y') for d in pv.index]
    n_months = len(month_labels)
    x = np.arange(n_months)

    # 创建双Y轴
    fig, ax1 = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor('white')
    ax2 = ax1.twinx()  # 创建右Y轴

    # ── 第一条折线（左Y轴） ──
    cat1 = categories[0]
    vals1 = pv[cat1].values.astype(float)
    color1 = colors.get(cat1, '#4472C4')
    ax1.plot(x, vals1, 'o-', color=color1, linewidth=2.5, markersize=6,
             markerfacecolor=color1, markeredgecolor='white',
             markeredgewidth=0.8, zorder=5, label=cat1)

    _set_embedded_chart_title(ax1, meta, font_prop)
    off1 = _label_offset(vals1)

    # 数据标签（百分比格式，1位小数，靠近数据点）
    for i, v in enumerate(vals1):
        ax1.text(x[i], v + off1, _fmt_value(v, cat1), ha='center', va='bottom',
                 fontsize=8.5, fontweight='bold', color=color1,
                 fontproperties=font_prop, zorder=6)

    # ── 第二条折线（右Y轴） ──
    if len(categories) > 1:
        cat2 = categories[1]
        vals2 = pv[cat2].values.astype(float)
        color2 = colors.get(cat2, '#ED7D31')
        ax2.plot(x, vals2, 'o-', color=color2, linewidth=2.5, markersize=6,
                 markerfacecolor=color2, markeredgecolor='white',
                 markeredgewidth=0.8, zorder=5, label=cat2)

        off2 = _label_offset(vals2)
        # 数据标签
        for i, v in enumerate(vals2):
            ax2.text(x[i], v + off2, _fmt_value(v, cat2), ha='center', va='bottom',
                     fontsize=8.5, fontweight='bold', color=color2,
                     fontproperties=font_prop, zorder=6)

    # ── Axis / styling ──
    # 小标题字体缩小到12
    # ax.set_title(chart_title, fontsize=12, fontweight='bold', color='#333',
    #              fontproperties=font_prop, pad=18)
    ax1.set_xticks(x)
    ax1.set_xticklabels(month_labels, fontsize=9.5, color='#555', fontproperties=font_prop)
    ax1.set_xlim(-0.4, n_months - 0.6)

    # 左Y轴：百分比格式
    ax1.yaxis.set_visible(True)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: _fmt_value(y, cat1)))
    ax1.tick_params(axis='y', labelsize=9.5, colors=color1, labelcolor=color1)
    ax1.yaxis.label.set_color(color1)

    # 右Y轴：百分比格式
    ax2.yaxis.set_visible(True)
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: _fmt_value(y, cat2)))
    ax2.tick_params(axis='y', labelsize=9.5, colors=color2, labelcolor=color2)
    ax2.yaxis.label.set_color(color2)

    # 去掉网格线
    ax1.grid(False)
    ax2.grid(False)

    # 去掉边框
    for spine in ax1.spines.values():
        spine.set_visible(False)
    for spine in ax2.spines.values():
        spine.set_visible(False)

    # ── Legend (合并两个轴的图例) ──
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper center',
               bbox_to_anchor=(0.5, -0.06), ncol=len(categories), fontsize=9.5,
               frameon=False, prop=font_prop, handlelength=1.5,
               handleheight=0.8, columnspacing=2.0)

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

    fig, ax1 = plt.subplots(figsize=_figsize(meta))
    fig.patch.set_facecolor('white')
    _set_embedded_chart_title(ax1, meta, font_prop)

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
                     fontsize=7.5, fontweight='bold', color='#555',
                     fontproperties=font_prop, zorder=6)

    ax1.set_ylabel(bar_col, fontsize=9.5, fontweight='bold', color='#333', fontproperties=font_prop)
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
            ax2.text(x[i], v + 0.005, _fmt_pct(v, cat), ha='center', va='bottom',
                     fontsize=8.5, fontweight='bold', color=color,
                     fontproperties=font_prop, zorder=6)

    ax2.set_ylabel('过件率', fontsize=9.5, fontweight='bold', color='#333', fontproperties=font_prop)
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: _fmt_pct(y, '过件率')))
    ax2.tick_params(axis='y', labelsize=10, colors='#555')

    # ── 共享 X 轴 ──
    # ax1.set_title(chart_title, fontsize=14, fontweight='bold', color='#333',
    #               fontproperties=font_prop, pad=18)  # 删除标题
    ax1.set_xticks(x)
    ax1.set_xticklabels(month_labels, fontsize=9.5, color='#555', fontproperties=font_prop)
    ax1.set_xlim(-0.6, n_months - 0.4)

    # 去掉网格线
    ax1.grid(False)

    # 去掉边框
    for spine in ax1.spines.values():
        spine.set_visible(False)
    for spine in ax2.spines.values():
        spine.set_visible(False)

    # ── Legend（合并两个轴的图例） ──
    handles1, labels1 = ax1.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(handles1 + handles2, labels1 + labels2,
               loc='upper center', bbox_to_anchor=(0.5, -0.06),
               ncol=len(categories), fontsize=9.5, frameon=False,
               prop=font_prop, handlelength=1.5, handleheight=0.8, columnspacing=2.0)

    plt.tight_layout(rect=[0, 0.04, 1, 1])
    return fig


def render_single_line(pivot_display, meta, styles, font_prop):
    """单折线图（用于竞得率整体等指标）。"""
    categories = meta['categories']
    chart_title = meta.get('chart_title', '')
    colors = styles.get('colors', {})

    figsize = _figsize(meta)

    pv = pivot_display
    month_labels = [d.strftime('%b-%y') for d in pv.index]
    n_months = len(month_labels)
    x = np.arange(n_months)

    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor('white')
    _set_embedded_chart_title(ax, meta, font_prop)

    # ── 单条折线 ──
    cat = categories[0]
    vals = pv[cat].values.astype(float)
    color = colors.get(cat, '#4472C4')
    ax.plot(x, vals, 'o-', color=color, linewidth=2.5, markersize=6,
            markerfacecolor=color, markeredgecolor='white',
            markeredgewidth=0.8, zorder=5, label=cat)

    _set_embedded_chart_title(ax, meta, font_prop)
    off = _label_offset(vals)

    # 数据标签（百分比格式，1位小数，靠近数据点）
    for i, v in enumerate(vals):
        ax.text(x[i], v + off, _fmt_value(v, cat), ha='center', va='bottom',
                fontsize=8.5, fontweight='bold', color=color,
                fontproperties=font_prop, zorder=6)

    # ── Axis / styling ──
    # ax.set_title(chart_title, fontsize=14, fontweight='bold', color='#333',
    #              fontproperties=font_prop, pad=18)  # 删除标题
    ax.set_xticks(x)
    ax.set_xticklabels(month_labels, fontsize=9.5, color='#555', fontproperties=font_prop)
    ax.set_xlim(-0.4, n_months - 0.6)

    # Y 轴：百分比格式
    ax.yaxis.set_visible(True)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: _fmt_value(y, cat)))
    ax.tick_params(axis='y', labelsize=9.5, colors='#555')

    # 去掉网格线
    ax.grid(False)

    # 去掉边框
    for spine in ax.spines.values():
        spine.set_visible(False)

    # ── Legend ──
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.06),
              ncol=1, fontsize=9.5, frameon=False,
              prop=font_prop, handlelength=1.5, handleheight=0.8)

    plt.tight_layout(rect=[0, 0.04, 1, 1])
    return fig


def render_multi_line_grouped(pivot_display, meta, styles, font_prop):
    """分组多折线图（用于竞得率-byV7preA等分组指标）。"""
    categories = meta['categories']
    chart_title = meta.get('chart_title', '')
    colors = styles.get('colors', {})

    figsize = _figsize(meta)

    pv = pivot_display
    month_labels = [d.strftime('%b-%y') for d in pv.index]
    n_months = len(month_labels)
    x = np.arange(n_months)

    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor('white')

    # ── 多条折线（每个分组一条） ──
    for cat in categories:
        if cat not in pv.columns:
            continue
        vals = pv[cat].values.astype(float)
        color = colors.get(cat, '#999999')
        off = _label_offset(vals)
        ax.plot(x, vals, 'o-', color=color, linewidth=2.2, markersize=5,
                markerfacecolor=color, markeredgecolor='white',
                markeredgewidth=0.8, zorder=5, label=cat)

        # 数据标签（仅标注部分月份以避免拥挤，靠近数据点）
        for i, v in enumerate(vals):
            if i % 2 == 0 or i == n_months - 1:  # 每隔一个月标注
                ax.text(x[i], v + off, _fmt_value(v, cat), ha='center', va='bottom',
                        fontsize=7.5, fontweight='bold', color=color,
                        fontproperties=font_prop, zorder=6)

    # ── Axis / styling ──
    # ax.set_title(chart_title, fontsize=14, fontweight='bold', color='#333',
    #              fontproperties=font_prop, pad=18)  # 删除标题
    ax.set_xticks(x)
    ax.set_xticklabels(month_labels, fontsize=9.5, color='#555', fontproperties=font_prop)
    ax.set_xlim(-0.4, n_months - 0.6)

    # Y 轴：百分比格式
    ax.yaxis.set_visible(True)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: _fmt_value(y, categories[0] if categories else '')))
    ax.tick_params(axis='y', labelsize=9.5, colors='#555')

    # 去掉网格线
    ax.grid(False)

    # 去掉边框
    for spine in ax.spines.values():
        spine.set_visible(False)

    # ── Legend ──
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.06),
              ncol=min(len(categories), 5), fontsize=9.5, frameon=False,
              prop=font_prop, handlelength=1.5, handleheight=0.8, columnspacing=2.0)

    plt.tight_layout(rect=[0, 0.04, 1, 1])
    return fig


def render_dual_line_with_bar(pivot_display, meta, styles, font_prop):
    """柱状图 + 双折线（用于渠道转化总览、请求参竞等）。"""
    categories = meta['categories']
    chart_title = meta.get('chart_title', '')
    colors = styles.get('colors', {})

    pv = pivot_display
    month_labels = [d.strftime('%b-%y') for d in pv.index]
    n_months = len(month_labels)
    x = np.arange(n_months)
    bw = 0.5

    fig, ax1 = plt.subplots(figsize=_figsize(meta))
    fig.patch.set_facecolor('white')
    _set_embedded_chart_title(ax1, meta, font_prop)

    # ── 左Y轴：柱状图（第一个指标，如日耗、请求数等） ──
    bar_col = categories[0]
    bar_vals = pv[bar_col].values.astype(float)
    bar_color = colors.get(bar_col, '#808080')

    ax1.bar(x, bar_vals, bw, color=bar_color, label=bar_col,
            edgecolor='white', linewidth=0.5, zorder=3)

    # 柱状图数据标签
    for i, v in enumerate(bar_vals):
        if v > 0:
            ax1.text(x[i], v * 0.05, f'{v:.1f}', ha='center', va='bottom',
                     fontsize=7.5, fontweight='bold', color='#555',
                     fontproperties=font_prop, zorder=6)

    ax1.set_ylabel(bar_col, fontsize=9.5, fontweight='bold', color='#333', fontproperties=font_prop)
    ax1.tick_params(axis='y', labelsize=10, colors='#555')
    ax1.set_ylim(0, max(bar_vals) * 1.15)
    ax1.yaxis.set_visible(True)

    # ── 右Y轴：双折线（其余指标） ──
    ax2 = ax1.twinx()

    line_cats = categories[1:]
    for cat in line_cats:
        if cat not in pv.columns:
            continue
        vals = pv[cat].values.astype(float)
        color = colors.get(cat, '#4472C4')
        ax2.plot(x, vals, 'o-', color=color, linewidth=2.5, markersize=5,
                 markerfacecolor=color, markeredgecolor='white',
                 markeredgewidth=0.8, zorder=5, label=cat)

        # 数据标签
        for i, v in enumerate(vals):
            # 根据值的大小决定标签格式
            if v < 1:  # 百分比
                label_text = _fmt_pct(v, cat)
            else:  # 数值
                label_text = f'{v:.0f}'
            ax2.text(x[i], v + max(vals) * 0.02, label_text, ha='center', va='bottom',
                     fontsize=8.5, fontweight='bold', color=color,
                     fontproperties=font_prop, zorder=6)

    ax2.set_ylabel('转化指标', fontsize=9.5, fontweight='bold', color='#333', fontproperties=font_prop)
    ax2.tick_params(axis='y', labelsize=10, colors='#555')

    # ── 共享 X 轴 ──
    # ax1.set_title(chart_title, fontsize=14, fontweight='bold', color='#333',
    #               fontproperties=font_prop, pad=18)  # 删除标题
    ax1.set_xticks(x)
    ax1.set_xticklabels(month_labels, fontsize=9.5, color='#555', fontproperties=font_prop)
    ax1.set_xlim(-0.6, n_months - 0.4)

    # 去掉网格线
    ax1.grid(False)

    # 去掉边框
    for spine in ax1.spines.values():
        spine.set_visible(False)
    for spine in ax2.spines.values():
        spine.set_visible(False)

    # ── Legend ──
    handles1, labels1 = ax1.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(handles1 + handles2, labels1 + labels2,
               loc='upper center', bbox_to_anchor=(0.5, -0.06),
               ncol=min(len(categories), 5), fontsize=9.5, frameon=False,
               prop=font_prop, handlelength=1.5, handleheight=0.8, columnspacing=2.0)

    plt.tight_layout(rect=[0, 0.04, 1, 1])
    return fig


def render_stacked_column_chart(pivot_display, meta, styles, font_prop):
    """双柱状 + 折线（用于精准授库结果）。"""
    categories = meta['categories']
    chart_title = meta.get('chart_title', '')
    colors = styles.get('colors', {})

    pv = pivot_display
    month_labels = [d.strftime('%b-%y') for d in pv.index]
    n_months = len(month_labels)
    x = np.arange(n_months)
    bw = 0.35

    fig, ax1 = plt.subplots(figsize=_figsize(meta))
    fig.patch.set_facecolor('white')

    # ── 左Y轴：并列柱状图（前两个指标，如授库量、可营销量） ──
    bar_cols = categories[:2]
    offsets = [-bw/2, bw/2]
    for bar_col, offset in zip(bar_cols, offsets):
        if bar_col not in pv.columns:
            continue
        bar_vals = pv[bar_col].values.astype(float)
        bar_color = colors.get(bar_col, '#4472C4')

        ax1.bar(x + offset, bar_vals, bw * 0.9, color=bar_color, label=bar_col,
                edgecolor='white', linewidth=0.5, zorder=3)

        # 数据标签
        for i, v in enumerate(bar_vals):
            if v > 0:
                ax1.text(x[i] + offset, v * 0.05, f'{v:.0f}', ha='center', va='bottom',
                         fontsize=7.5, fontweight='bold', color='#555',
                         fontproperties=font_prop, zorder=6)

    ax1.set_ylabel('数量', fontsize=9.5, fontweight='bold', color='#333', fontproperties=font_prop)
    ax1.tick_params(axis='y', labelsize=10, colors='#555')
    max_bar_val = max(pv[bar_cols].max().max(), 1)
    ax1.set_ylim(0, max_bar_val * 1.15)
    ax1.yaxis.set_visible(True)

    # ── 右Y轴：折线（第三个指标，如可营销率） ──
    if len(categories) > 2:
        ax2 = ax1.twinx()
        line_col = categories[2]
        if line_col in pv.columns:
            vals = pv[line_col].values.astype(float)
            color = colors.get(line_col, '#808080')
            ax2.plot(x, vals, 'o-', color=color, linewidth=2.5, markersize=5,
                     markerfacecolor=color, markeredgecolor='white',
                     markeredgewidth=0.8, zorder=5, label=line_col)

            # 数据标签（百分比格式）
            for i, v in enumerate(vals):
                ax2.text(x[i], v + 0.005, _fmt_pct(v, line_col), ha='center', va='bottom',
                         fontsize=8.5, fontweight='bold', color=color,
                         fontproperties=font_prop, zorder=6)

            ax2.set_ylabel('率指标', fontsize=9.5, fontweight='bold', color='#333', fontproperties=font_prop)
            ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: _fmt_pct(y, line_col)))
            ax2.tick_params(axis='y', labelsize=10, colors='#555')

    # ── 共享 X 轴 ──
#     ax1.set_title(chart_title, fontsize=12, fontweight='bold', color='#333',
#                   fontproperties=font_prop, pad=18)
    ax1.set_xticks(x)
    ax1.set_xticklabels(month_labels, fontsize=9.5, color='#555', fontproperties=font_prop)
    ax1.set_xlim(-0.6, n_months - 0.4)

    # 网格��
    ax1.grid(False)

    # 边框
    for spine in ax1.spines.values():
        spine.set_visible(False)
    if len(categories) > 2:
        for spine in ax2.spines.values():
            spine.set_visible(False)

    # ── Legend ──
    handles1, labels1 = ax1.get_legend_handles_labels()
    if len(categories) > 2:
        handles2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(handles1 + handles2, labels1 + labels2,
                   loc='upper center', bbox_to_anchor=(0.5, -0.06),
                   ncol=len(categories), fontsize=9.5, frameon=False,
                   prop=font_prop, handlelength=1.5, handleheight=0.8, columnspacing=2.0)
    else:
        ax1.legend(loc='upper center', bbox_to_anchor=(0.5, -0.06),
                   ncol=len(bar_cols), fontsize=9.5, frameon=False,
                   prop=font_prop, handlelength=1.5, handleheight=0.8)

    plt.tight_layout(rect=[0, 0.04, 1, 1])
    return fig


# ── 图表类型注册表 ──
CHART_RENDERERS = {
    'stacked_bar_line': render_stacked_bar_line,
    'dual_line': render_dual_line,
    'bar_multi_line': render_bar_multi_line,
    'single_line': render_single_line,                   # 新增
    'multi_line_grouped': render_multi_line_grouped,     # 新增
    'dual_line_with_bar': render_dual_line_with_bar,     # 新增
    'stacked_column_chart': render_stacked_column_chart, # 新增
}
