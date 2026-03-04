# -*- coding: utf-8 -*-
"""分析模板注册表 — analysis_template 名称 → 分析函数映射"""

import pandas as pd


def trade_mom(pivot_display: pd.DataFrame, meta: dict) -> list[str]:
    """
    交易环比分析模板。
    pivot_display: 已按 unit_divisor 转换后的透视表（如：亿为单位）。
    返回分析文字列表。
    """
    categories = meta['categories']
    report_month = pd.Timestamp(meta['report_month'] + '-01')
    unit = meta.get('unit', '')

    pv = pivot_display
    curr = pv.loc[report_month]
    prev_m = pv.index[pv.index < report_month][-1]
    prev = pv.loc[prev_m]

    t_curr, t_prev = curr['总计'], prev['总计']
    diff = t_curr - t_prev
    pct = diff / t_prev * 100
    mn, pmn = report_month.month, prev_m.month

    # 各分类变化
    segs = []
    for c in categories:
        vc, vp = curr[c], prev[c]
        sd = vc - vp
        sp = sd / vp * 100 if vp > 0.01 else (-100 if vc < 0.01 else 0)
        segs.append(dict(name=c, curr=vc, prev=vp, diff=sd, pct=sp))
    segs.sort(key=lambda s: abs(s['diff']), reverse=True)

    declining = [s for s in segs if s['diff'] < -0.005]
    all_decline = len(declining) >= len(categories) - 1

    # 峰值和连续下降
    totals = pv['总计']
    streak = 0
    for i in range(len(totals) - 1, 0, -1):
        if totals.iloc[i] < totals.iloc[i - 1]:
            streak += 1
        else:
            break
    if streak > 0:
        streak_start_idx = len(totals) - 1 - streak
        peak_m = totals.index[streak_start_idx]
        peak_val = totals.iloc[streak_start_idx]
    else:
        peak_val = totals.max()
        peak_m = totals.idxmax()

    # ── Line 1: 总量概览 ──
    dir_word = "减少" if diff < 0 else "增加"
    chg_word = "下降" if diff < 0 else "上升"
    line1 = (f"{mn}月1-7评级首借交易（24h口径）总额{t_curr:.2f}{unit}元，"
             f"环比{pmn}月{dir_word}{abs(diff):.1f}{unit}，{chg_word}{abs(pct):.1f}%；")

    # ── Line 2: 驱动分析 ──
    top1, top2 = segs[0], segs[1]
    if all_decline:
        parts = []
        parts.append(f"{top1['name']}{dir_word}{abs(top1['diff']):.1f}{unit}（降{abs(top1['pct']):.0f}%）为主要拖累项")
        valid = [s for s in declining if s['prev'] > 0.05 and s['name'] != top1['name']]
        if valid:
            st = max(valid, key=lambda s: abs(s['pct']))
            parts.append(f"{st['name']}降幅最大（降{abs(st['pct']):.0f}%）")
        api = next((s for s in segs if s['name'] == 'API回流'), None)
        if api and api['curr'] < 0.02:
            parts.append("API回流趋近于零")
        line2 = "各客群交易全线收缩，" + "，".join(parts) + "。"
    else:
        up = [s for s in segs if s['diff'] > 0.01]
        dn = [s for s in segs if s['diff'] < -0.01]
        parts = []
        if dn:
            parts.append(f"{dn[0]['name']}减少{abs(dn[0]['diff']):.1f}{unit}")
        if up:
            parts.append(f"{up[0]['name']}增加{abs(up[0]['diff']):.1f}{unit}")
        line2 = "主要变化：" + "，".join(parts) + "。"

    # ── Line 3: 趋势（可选）──
    if streak >= 4:
        line3 = f"自{peak_m.year}年{peak_m.month}月高峰（{peak_val:.1f}{unit}）以来已连续{streak}个月下滑。"
    else:
        line3 = ""

    return [l for l in [line1, line2, line3] if l]


# ── 模板注册表 ──
ANALYSIS_TEMPLATES = {
    'trade_mom': trade_mom,
}
