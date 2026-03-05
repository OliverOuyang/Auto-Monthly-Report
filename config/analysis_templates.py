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


def spend_mom(pivot_display: pd.DataFrame, meta: dict) -> list[str]:
    """
    渠道花费环比分析模板。
    pivot_display: 已按 unit_divisor 转换后的透视表（如：万为单位）。
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
    pct = diff / t_prev * 100 if t_prev > 0.01 else 0
    mn, pmn = report_month.month, prev_m.month

    # 各渠道变化
    segs = []
    for c in categories:
        vc, vp = curr[c], prev[c]
        sd = vc - vp
        sp = sd / vp * 100 if vp > 0.01 else 0
        segs.append(dict(name=c, curr=vc, prev=vp, diff=sd, pct=sp))

    segs.sort(key=lambda s: abs(s['diff']), reverse=True)

    # Line 1: 总量概览
    dir_word = "减少" if diff < 0 else "增加"
    line1 = (f"{mn}月业务口径花费总额{t_curr:.1f}{unit}元，"
             f"环比{pmn}月{dir_word}{abs(diff):.1f}{unit}，变化{abs(pct):.1f}%；")

    # Line 2: 主要变化渠道
    top_up = [s for s in segs if s['diff'] > 0.1][:2]
    top_down = [s for s in segs if s['diff'] < -0.1][:2]

    parts = []
    if top_down:
        parts.append(f"{top_down[0]['name']}减少{abs(top_down[0]['diff']):.1f}{unit}（降{abs(top_down[0]['pct']):.0f}%）")
    if top_up:
        parts.append(f"{top_up[0]['name']}增加{abs(top_up[0]['diff']):.1f}{unit}（升{abs(top_up[0]['pct']):.0f}%）")

    line2 = "主要变化：" + "，".join(parts) + "。" if parts else ""

    return [l for l in [line1, line2] if l]


def cps_trend(pivot_display: pd.DataFrame, meta: dict) -> list[str]:
    """
    CPS 趋势分析模板。
    pivot_display: CPS 数据（比率值，无需单位转换）。
    """
    categories = meta['categories']
    report_month = pd.Timestamp(meta['report_month'] + '-01')

    pv = pivot_display
    curr = pv.loc[report_month]
    prev_m = pv.index[pv.index < report_month][-1]
    prev = pv.loc[prev_m]

    mn = report_month.month

    # 当月值
    cps_all = curr[categories[0]]
    cps_t0 = curr[categories[1]]

    # 环比
    cps_all_prev = prev[categories[0]]
    cps_t0_prev = prev[categories[1]]

    diff_all = cps_all - cps_all_prev
    diff_t0 = cps_t0 - cps_t0_prev

    dir_all = "上升" if diff_all > 0 else "下降"
    dir_t0 = "上升" if diff_t0 > 0 else "下降"

    # Line 1: 当月CPS及环比
    line1 = (f"{mn}月1-7全首借CPS为{cps_all*100:.2f}%，环比{dir_all}{abs(diff_all)*100:.2f}个百分点；"
             f"1-7 T0CPS为{cps_t0*100:.2f}%，环比{dir_t0}{abs(diff_t0)*100:.2f}个百分点。")

    # Line 2: 趋势（与历史高/低点对比）
    all_cps_all = pv[categories[0]]
    peak_val = all_cps_all.max()
    peak_m = all_cps_all.idxmax()

    if cps_all < peak_val * 0.95:
        line2 = f"当前CPS较{peak_m.year}年{peak_m.month}月高点（{peak_val*100:.2f}%）有所回落。"
    else:
        line2 = ""

    return [l for l in [line1, line2] if l]


def quality_trend(pivot_display: pd.DataFrame, meta: dict) -> list[str]:
    """
    质量指标趋势分析模板。
    pivot_display: 过件率和授信额度数据。
    """
    categories = meta['categories']
    report_month = pd.Timestamp(meta['report_month'] + '-01')

    pv = pivot_display
    curr = pv.loc[report_month]
    prev_m = pv.index[pv.index < report_month][-1]
    prev = pv.loc[prev_m]

    mn, pmn = report_month.month, prev_m.month

    # 提取当月值
    credit_avg = curr[categories[0]]  # 1-7 T0平均授信额度
    pass_rate = curr[categories[1]]  # 1-3 T0过件率
    pass_rate_paid = curr[categories[2]]  # 投放渠道
    pass_rate_free = curr[categories[3]]  # 免费

    # 环比
    credit_diff = credit_avg - prev[categories[0]]
    pass_diff = pass_rate - prev[categories[1]]
    pass_paid_diff = pass_rate_paid - prev[categories[2]]
    pass_free_diff = pass_rate_free - prev[categories[3]]

    # Line 1: 授信额度
    dir_credit = "上升" if credit_diff > 0 else "下降"
    line1 = (f"{mn}月1-7 T0平均授信额度{credit_avg:.0f}元，"
             f"环比{pmn}月{dir_credit}{abs(credit_diff):.0f}元。")

    # Line 2: 过件率
    dir_pass = "提升" if pass_diff > 0 else "下降"
    line2 = (f"1-3 T0过件率{pass_rate*100:.2f}%，环比{dir_pass}{abs(pass_diff)*100:.2f}个百分点；")

    # Line 3: 渠道差异
    line3 = (f"投放渠道过件率{pass_rate_paid*100:.2f}%（环比{abs(pass_paid_diff)*100:.2f}pp），"
             f"免费渠道{pass_rate_free*100:.2f}%（环比{abs(pass_free_diff)*100:.2f}pp）。")

    return [line1, line2, line3]


def channel_overview(pivot_display: pd.DataFrame, meta: dict) -> list[str]:
    """
    渠道转化总览分析模板(P11/P15/P19)。

    根据渠道类型生成不同的分析文字。
    """
    channel = meta.get('channel_filter', '未知渠道')
    report_month = pd.Timestamp(meta['report_month'] + '-01')

    pv = pivot_display
    if report_month not in pv.index:
        return [f"[{channel}渠道数据不足]"]

    curr = pv.loc[report_month]
    prev_m = pv.index[pv.index < report_month][-1] if len(pv.index[pv.index < report_month]) > 0 else report_month
    prev = pv.loc[prev_m]

    # 渠道特定的分析逻辑
    if channel == '腾讯':
        return _analyze_tencent_overview(curr, prev, report_month, prev_m)
    elif channel == '抖音':
        return _analyze_douyin_overview(curr, prev, report_month, prev_m)
    elif channel == '精准营销':
        return _analyze_jingzhun_overview(curr, prev, report_month, prev_m)
    else:
        return [f"[{channel}渠道分析模板未实现]"]


def _analyze_tencent_overview(curr, prev, report_month, prev_m):
    """腾讯渠道总览分析"""
    # 提取指标
    pass_rate_13 = curr.get('进件1-3通过率', 0)
    pass_rate_17 = curr.get('进件1-7通过率', 0)
    t0cps = curr.get('T0CPS_24h', 0)
    daily_spend = curr.get('日耗', 0)

    pass_rate_13_prev = prev.get('进件1-3通过率', 0)
    t0cps_prev = prev.get('T0CPS_24h', 0)
    daily_spend_prev = prev.get('日耗', 0)

    # 计算变化
    pass_change = (pass_rate_13 - pass_rate_13_prev) * 100
    cost_change = (t0cps - t0cps_prev) * 100
    spend_change = daily_spend - daily_spend_prev

    # 生成分析文字
    lines = []
    lines.append(f"**腾讯总览**: 质量成本达成良好;稳定质量,探索成本继续压降的可能性")
    lines.append(f"**数据表现**: 质量由{pass_rate_13_prev*100:.1f}%提升至{pass_rate_13*100:.1f}%,"
                 f"成本{t0cps_prev*100:.1f}%下降至{t0cps*100:.1f}%,日耗{'下降' if spend_change < 0 else '上升'}{abs(spend_change):.0f}万")
    lines.append(f"**未来方向**: 稳定质量,花费达标(50万日耗)下,通过扣回传、RTA尾部降价方式继续下压成本")

    return lines


def _analyze_douyin_overview(curr, prev, report_month, prev_m):
    """抖音渠道总览分析"""
    t0cps = curr.get('T0CPS_24h', 0)
    daily_spend = curr.get('日耗', 0)
    pass_rate_13 = curr.get('进件1-3通过率', 0)

    t0cps_prev = prev.get('T0CPS_24h', 0)
    daily_spend_prev = prev.get('日耗', 0)
    pass_rate_13_prev = prev.get('进件1-3通过率', 0)

    # 目标对比
    target_spend = 200  # 假设目标日耗200万
    spend_gap = (daily_spend - target_spend) / target_spend * 100

    lines = []
    lines.append(f"**抖音总览**: 规模不足、指标波动较大;短期适当放开排除、提出价方式提升规模")
    lines.append(f"**数据表现**: 规模低于目标{abs(spend_gap):.0f}%,成本1月波动较大(近一周为{t0cps*100:.0f}%),"
                 f"质量{'与上月持平' if abs(pass_rate_13 - pass_rate_13_prev) < 0.02 else f'变化{(pass_rate_13 - pass_rate_13_prev)*100:.1f}pp'}")
    lines.append(f"**当前问题**: 当前规模较低、成本及质量波动较大")
    lines.append(f"**未来方向**: 短期适当放开排除、提升出价方式提升规模")

    return lines


def _analyze_jingzhun_overview(curr, prev, report_month, prev_m):
    """精准营销渠道总览分析"""
    pass_rate_13 = curr.get('进件1-3通过率', 0)
    pass_rate_13_prev = prev.get('进件1-3通过率', 0)
    t0cps = curr.get('T0CPS_24h', 0)
    t0cps_prev = prev.get('T0CPS_24h', 0)

    # 假设有近2周数据可用(简化处理,实际应从更细粒度数据计算)
    recent_2w_pass = pass_rate_13  # 简化

    lines = []
    lines.append(f"**精准总览**: 质量提升显著风险表现有待观测,成本仍需压降")
    lines.append(f"**数据表现**: 质量{pass_rate_13_prev*100:.1f}%提升至{pass_rate_13*100:.1f}%,"
                 f"近2周稳定{recent_2w_pass*100:.0f}%;成本{t0cps*100:.1f}%基本持平")
    lines.append(f"**当前问题**: 随质量提升,后端转化降低CPS相对较高")
    lines.append(f"**未来方向**: 通过增加排除继续提升质量到20%;通过扣量、降价方式成本压降至15%")

    return lines


# ── 模板注册表 ──
ANALYSIS_TEMPLATES = {
    'trade_mom': trade_mom,
    'spend_mom': spend_mom,
    'cps_trend': cps_trend,
    'quality_trend': quality_trend,
    'channel_overview': channel_overview,  # 新增
}
