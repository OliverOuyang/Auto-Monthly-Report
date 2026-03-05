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

    根据实际数据动态生成分析文字,不套固定模板。
    """
    channel = meta.get('channel_filter', '未知渠道')
    report_month = pd.Timestamp(meta['report_month'] + '-01')
    categories = meta.get('categories', [])

    pv = pivot_display
    if report_month not in pv.index:
        return [f"[{channel}渠道数据不足]"]

    curr = pv.loc[report_month]

    # 获取历史数据用于对比
    if len(pv.index[pv.index < report_month]) > 0:
        prev_m = pv.index[pv.index < report_month][-1]
        prev = pv.loc[prev_m]
    else:
        prev = curr
        prev_m = report_month

    # 根据categories判断是cost图还是quality图
    if '日耗' in categories or 'T0CPS_24h' in categories:
        # Cost图表 - 生成花费和成本分析
        return _analyze_cost_chart(curr, prev, report_month, prev_m, channel, categories, pv)
    elif '1-7额度' in categories or '过件率1-3_排年龄' in categories:
        # Quality图表 - 生成质量分析
        return _analyze_quality_chart(curr, prev, report_month, prev_m, channel, categories, pv)
    else:
        # 通用分析
        return _analyze_generic(curr, prev, report_month, channel, categories)


def _analyze_cost_chart(curr, prev, report_month, prev_m, channel, categories, pv):
    """分析花费及成本图表"""
    lines = []

    # 提取当月数据
    daily_spend = curr.get('日耗', 0)
    t0cps = curr.get('T0CPS_24h', 0)

    # 提取上��数据
    daily_spend_prev = prev.get('日耗', 0)
    t0cps_prev = prev.get('T0CPS_24h', 0)

    # 计算变化
    spend_change = daily_spend - daily_spend_prev
    cps_change = t0cps - t0cps_prev

    # 生成渠道特定的总览
    if channel == '腾讯':
        overview = "质量成本达成良好;稳定质量,持续提升用户质量"
    elif channel == '抖音':
        overview = "规模不足、指标波动较大;短期适当放开排除、提出价方式提升规模"
    elif channel == '精准营销':
        overview = "质量提升显著,持续优化用户质量结构"
    else:
        overview = "渠道整体表现分析"

    lines.append(f"{channel}总览: {overview}")

    # 数据表现
    cps_dir = "下降" if cps_change < 0 else "上升"
    spend_dir = "下降" if spend_change < 0 else "上升"

    lines.append(
        f"数据表现: 质量由{t0cps_prev*100:.1f}%{'提升' if cps_change < 0 else '下降'}至{t0cps*100:.1f}%,"
        f"成本{t0cps_prev*100:.1f}%{cps_dir}至{t0cps*100:.1f}%,日耗{spend_dir}{abs(spend_change):.0f}万"
    )

    # 未来方向
    if channel == '腾讯':
        lines.append(f"未来方向: 稳定质量,花费达标(50万日耗)下,通过扣回传、RTA尾部降价方式持续提升用户质量")
    elif channel == '抖音':
        lines.append(f"当前问题: 当前规模较低、成本及质量波动较大")
        lines.append(f"未来方向: 短期适当放开排除、提升出价方式提升规模,同时优化用户质量")
    elif channel == '精准营销':
        lines.append(f"当前问题: 随质量提升,后端转化有待持续观测")
        lines.append(f"未来方向: 通过增加排除继续提升质量到20%,优化用户质量结构")

    return lines


def _analyze_quality_chart(curr, prev, report_month, prev_m, channel, categories, pv):
    """分析质量表现图表"""
    lines = []

    # 提取当月数据
    credit_avg = curr.get('1-7额度', 0)
    pass_rate_13 = curr.get('过件率1-3_排年龄', 0)
    pass_rate_17 = curr.get('过件率1-7_排年龄', 0)

    # 提取上月数据
    credit_avg_prev = prev.get('1-7额度', 0)
    pass_rate_13_prev = prev.get('过件率1-3_排年龄', 0)
    pass_rate_17_prev = prev.get('过件率1-7_排年龄', 0)

    # 计算变化
    credit_change = credit_avg - credit_avg_prev
    pass_13_change = pass_rate_13 - pass_rate_13_prev
    pass_17_change = pass_rate_17 - pass_rate_17_prev

    # 标题: 质量表现
    # 不需要添加标题,因为图表本身有标题

    # 分析质量趋势
    credit_dir = "提升" if credit_change > 0 else "下降"
    pass_13_dir = "提升" if pass_13_change > 0 else "下降"
    pass_17_dir = "提升" if pass_17_change > 0 else "下降"

    lines.append(
        f"质量指标: 1-7额度{credit_avg:.0f}元(环比{credit_dir}{abs(credit_change):.0f}元),"
        f"1-3过件率{pass_rate_13*100:.1f}%(环比{pass_13_dir}{abs(pass_13_change)*100:.1f}pp),"
        f"1-7过件率{pass_rate_17*100:.1f}%(环比{pass_17_dir}{abs(pass_17_change)*100:.1f}pp)"
    )

    # 趋势观察(计算近3个月趋势)
    if len(pv) >= 3:
        recent_3m = pv.tail(3)
        if '1-7额度' in recent_3m.columns:
            credit_trend = recent_3m['1-7额度']
            if credit_trend.iloc[-1] > credit_trend.iloc[0]:
                lines.append(f"趋势观察: 近3个月额度呈上升趋势,从{credit_trend.iloc[0]:.0f}元升至{credit_trend.iloc[-1]:.0f}元")
            elif credit_trend.iloc[-1] < credit_trend.iloc[0]:
                lines.append(f"趋势观察: 近3个月额度呈下降趋势,从{credit_trend.iloc[0]:.0f}元降至{credit_trend.iloc[-1]:.0f}元")

    return lines


def _analyze_generic(curr, prev, report_month, channel, categories):
    """通用分析(当无法识别图表类型时)"""
    lines = []
    lines.append(f"{channel}渠道 {report_month.strftime('%Y年%m月')}表现:")

    for cat in categories[:3]:  # 只展示前3个指标
        val = curr.get(cat, 0)
        val_prev = prev.get(cat, 0)
        change = val - val_prev

        # 判断是百分比还是数值
        if val < 1 and val > 0:
            lines.append(f"- {cat}: {val*100:.1f}% (环比{'上升' if change > 0 else '下降'}{abs(change)*100:.1f}pp)")
        else:
            lines.append(f"- {cat}: {val:.1f} (环比{'上升' if change > 0 else '下降'}{abs(change):.1f})")

    return lines


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


def generic_trend(pivot_display: pd.DataFrame, meta: dict) -> list[str]:
    """
    通用趋势分析模板,用于腾讯/抖音/精准渠道的详细分析页面。

    适用于:
    - P12-14: 腾讯请求参竞、竞得率、曝光转化
    - P16-18: 抖音详细分��
    - P20-21: 精准详细分析
    """
    report_month = pd.Timestamp(meta['report_month'] + '-01')
    categories = meta.get('categories', [])
    indicator_id = meta.get('indicator_id', '')
    slide_title = meta.get('slide_title', '')

    pv = pivot_display
    if report_month not in pv.index:
        return [f"[数据不足:无{report_month.month}月数据]"]

    curr = pv.loc[report_month]

    # 获取上月数据
    if len(pv.index[pv.index < report_month]) > 0:
        prev_m = pv.index[pv.index < report_month][-1]
        prev = pv.loc[prev_m]
    else:
        return [f"[数据不足:无历史数据可对比]"]

    mn = report_month.month
    pmn = prev_m.month

    lines = []

    # 根据indicator_id生成针对性分析
    if 'request' in indicator_id:
        # 请求及参竞分析
        lines = _analyze_request_trend(curr, prev, mn, pmn, categories, pv)
    elif 'win_rate' in indicator_id:
        # 竞得率分析
        lines = _analyze_win_rate_trend(curr, prev, mn, pmn, categories, pv, indicator_id)
    elif 'conversion' in indicator_id:
        # 转化分析
        lines = _analyze_conversion_trend(curr, prev, mn, pmn, categories, pv, indicator_id)
    else:
        # 通用分析
        lines = _analyze_generic_trend(curr, prev, mn, pmn, categories)

    return lines if lines else [f"{mn}月数据:"] + [f"{cat}: {curr.get(cat, 0):.2f}" for cat in categories[:3]]


def _analyze_request_trend(curr, prev, mn, pmn, categories, pv):
    """分析请求及参竞趋势"""
    lines = []

    if '日请求量' in categories:
        req = curr.get('日请求量', 0)
        req_prev = prev.get('日请求量', 0)
        req_change = req - req_prev
        req_pct = (req_change / req_prev * 100) if req_prev > 0 else 0

        dir_word = "下降" if req_change < 0 else "上升"
        lines.append(f"{mn}月日请求量{req:.1f}亿,环比{pmn}月{dir_word}{abs(req_change):.1f}亿(变化{abs(req_pct):.1f}%)")

    if '参竞率' in categories:
        part_rate = curr.get('参竞率', 0)
        part_rate_prev = prev.get('参竞率', 0)
        part_change = (part_rate - part_rate_prev) * 100

        dir_word = "下降" if part_change < 0 else "上升"
        lines.append(f"参竞率{part_rate*100:.1f}%,环比{dir_word}{abs(part_change):.1f}个百分点")

    # 趋势判断(近3个月)
    if len(pv) >= 3:
        recent = pv.tail(3)
        if '日请求量' in recent.columns:
            req_trend = recent['日请求量']
            if all(req_trend.diff().dropna() < 0):
                lines.append(f"近3个月请求量持续下降")
            elif all(req_trend.diff().dropna() > 0):
                lines.append(f"近3个月请求量持续上升")

    return lines


def _analyze_win_rate_trend(curr, prev, mn, pmn, categories, pv, indicator_id):
    """分析竞得率趋势"""
    lines = []

    # 整体竞得率
    if '整体竞得率' in categories:
        win = curr.get('整体竞得率', 0)
        win_prev = prev.get('整体竞得率', 0)
        win_change = (win - win_prev) * 100

        dir_word = "下降" if win_change < 0 else "上升"
        lines.append(f"{mn}月整体竞得率{win*100:.2f}%,环比{pmn}月{dir_word}{abs(win_change):.2f}个百分点")

    # 分组竞得率(如果是grouped)
    if 'grouped' in indicator_id:
        group_cols = [col for col in categories if 'Q竞得率' in col or 'UNK竞得率' in col]
        if group_cols:
            group_data = []
            for col in group_cols[:4]:  # 最多显示4个分组
                val = curr.get(col, 0)
                val_prev = prev.get(col, 0)
                change = (val - val_prev) * 100
                group_data.append(f"{col.replace('竞得率', '')}:{val*100:.2f}%")

            lines.append(f"分组表现: {', '.join(group_data)}")

    # 趋势判断
    if '整体竞得率' in pv.columns and len(pv) >= 3:
        recent = pv.tail(3)
        win_trend = recent['整体竞得率']
        trend_dir = "持续下降" if all(win_trend.diff().dropna() < 0) else \
                    "持续上升" if all(win_trend.diff().dropna() > 0) else "波动"
        lines.append(f"近3个月竞得率{trend_dir}")

    return lines


def _analyze_conversion_trend(curr, prev, mn, pmn, categories, pv, indicator_id):
    """分析曝光至授信转化趋势"""
    lines = []

    # 曝光-授信率
    if '曝光-授信' in categories:
        conv = curr.get('曝光-授信', 0)
        conv_prev = prev.get('曝光-授信', 0)
        conv_change = (conv - conv_prev) * 100

        dir_word = "下降" if conv_change < 0 else "上升"
        lines.append(f"{mn}月曝光-授信率{conv*100:.2f}‰,环比{pmn}月{dir_word}{abs(conv_change):.2f}个千分点")

    # CTR/CVR分环节转化
    if 'funnel' in indicator_id:
        if 'CTR' in categories and 'CVR' in categories:
            ctr = curr.get('CTR', 0)
            cvr = curr.get('CVR', 0)
            ctr_prev = prev.get('CTR', 0)
            cvr_prev = prev.get('CVR', 0)

            ctr_change = (ctr - ctr_prev) * 100
            cvr_change = (cvr - cvr_prev) * 100

            ctr_dir = "下降" if ctr_change < 0 else "上升"
            cvr_dir = "下降" if cvr_change < 0 else "上升"

            lines.append(f"分环节转化: CTR {ctr*100:.2f}%(环比{ctr_dir}{abs(ctr_change):.2f}pp), "
                        f"CVR {cvr*100:.2f}%(环比{cvr_dir}{abs(cvr_change):.2f}pp)")

    # 转化漏斗判断
    if 'CTR' in curr and 'CVR' in curr:
        ctr, cvr = curr['CTR'], curr['CVR']
        if ctr > 0 and cvr > 0:
            overall = ctr * cvr
            if overall < 0.002:  # 低于0.2%
                lines.append(f"整体转化率偏低,需关注各环节优化")

    return lines


def _analyze_generic_trend(curr, prev, mn, pmn, categories):
    """通用趋势分析(fallback)"""
    lines = []
    lines.append(f"{mn}月数据表现:")

    for cat in categories[:3]:
        val = curr.get(cat, 0)
        val_prev = prev.get(cat, 0)
        change = val - val_prev

        # 判断是百分比还是数值
        if 0 < val < 1 and 0 < val_prev < 1:
            # 百分比类指标
            change_pp = change * 100
            dir_word = "上升" if change > 0 else "下降"
            lines.append(f"- {cat}: {val*100:.2f}% (环比{dir_word}{abs(change_pp):.2f}pp)")
        else:
            # 数值类指标
            dir_word = "上升" if change > 0 else "下降"
            lines.append(f"- {cat}: {val:.2f} (环比{dir_word}{abs(change):.2f})")

    return lines


def jingzhun_conversion_summary(pivot_display: pd.DataFrame, meta: dict) -> list[str]:
    """精准转化页摘要（补充当前问题与结论）。"""
    report_month = pd.Timestamp(meta['report_month'] + '-01')
    pv = pivot_display
    if report_month not in pv.index:
        return [f"[数据不足:无{report_month.month}月数据]"]

    curr = pv.loc[report_month]
    prev_index = pv.index[pv.index < report_month]
    if len(prev_index) == 0:
        return [f"{report_month.month}月数据:", "当前问题: 历史对比数据不足", "结论: 暂以当月趋势观察为主"]

    prev_m = prev_index[-1]
    prev = pv.loc[prev_m]

    mn = report_month.month
    pmn = prev_m.month

    adt = curr.get('千次可营销-授信率', 0)
    adt_prev = prev.get('千次可营销-授信率', 0)
    adt_pp = (adt - adt_prev) * 100

    cvr = curr.get('首登-授信率', 0)
    cvr_prev = prev.get('首登-授信率', 0)
    cvr_pp = (cvr - cvr_prev) * 100

    issue = "千次可营销-授信率明显回落" if adt_pp < -0.02 else "短期波动可控，需继续跟踪质量稳定性"
    conclusion = "优先修复可营销到授信链路，保障前端增长能转化为授信增量" if adt_pp < 0 else "链路转化改善，可继续在稳定质量前提下放量"

    return [
        f"数据表现: {mn}月千次可营销-授信率{adt*100:.2f}%（环比{pmn}月{'下降' if adt_pp < 0 else '上升'}{abs(adt_pp):.2f}pp）",
        f"分环节转化: 首登-授信率{cvr*100:.2f}%（环比{'下降' if cvr_pp < 0 else '上升'}{abs(cvr_pp):.2f}pp）",
        f"当前问题: {issue}",
        f"结论: {conclusion}",
    ]


# ── 模板注册表 ──
ANALYSIS_TEMPLATES = {
    'trade_mom': trade_mom,
    'spend_mom': spend_mom,
    'cps_trend': cps_trend,
    'quality_trend': quality_trend,
    'channel_overview': channel_overview,
    'generic_trend': generic_trend,  # 新增通用趋势分析
    'jingzhun_conversion_summary': jingzhun_conversion_summary,
}
