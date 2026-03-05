# -*- coding: utf-8 -*-
"""按 meta 规则从 raw data 构建结构表（透视表）"""

import pandas as pd
import numpy as np


def build_pivot(raw: pd.DataFrame, meta: dict) -> pd.DataFrame:
    """
    按 meta 配置从 raw DataFrame 生成透视表。

    步骤：
    1. 过滤 filter_exclude 值
    2. 应用 merge_rules 合并分类
    3. pivot_table 聚合
    4. 按 report_month 截止
    5. 按 categories 排序列 + 总计
    """
    time_col = meta['time_column']
    group_col = meta['group_column']
    value_col = meta['value_column']
    agg_func = meta['agg_func']
    categories = meta['categories']
    filter_exclude = meta.get('filter_exclude', [])
    merge_rules = meta.get('merge_rules', {})
    report_month = pd.Timestamp(meta['report_month'] + '-01')
    indicator_id = meta.get('indicator_id', '')

    df = raw.copy()

    # 确保时间列为 datetime
    df[time_col] = pd.to_datetime(df[time_col])

    # 确保值列为数值
    df[value_col] = pd.to_numeric(df[value_col], errors='coerce').fillna(0)

    # 1. 过滤
    # 按照 meta 配置中的 filter_exclude 过滤数据
    if filter_exclude:
        df = df[~df[group_col].isin(filter_exclude)]

    # 2. 合并分类
    if merge_rules:
        group_col_merged = group_col + '_merged'
        df[group_col_merged] = df[group_col].replace(merge_rules)
    else:
        group_col_merged = group_col

    # 3. 透视
    pivot = df.pivot_table(
        index=time_col,
        columns=group_col_merged,
        values=value_col,
        aggfunc=agg_func,
        fill_value=0
    ).sort_index()

    # 4. 截止到 report_month
    pivot = pivot.loc[pivot.index <= report_month]

    # 5. 按 categories 排序列
    pivot = pivot.reindex(columns=categories, fill_value=0)

    # 6. 总计列
    if meta.get('show_total_line', True):
        pivot['总计'] = pivot[categories].sum(axis=1)

    return pivot


def build_cps_all_channel_pivot(excel_path: str, meta: dict) -> pd.DataFrame:
    """
    构建 CPS 指标透视表（跨表计算）。

    CPS = 花费 / 交易额

    涉及表：
    - 2_花费: 业务口径花费（filter: 去掉其他、免费渠道）
    - _manual_inputs: 促申完花费 + RTA花费
    - 1_首借交易: 首借交易总额（filter: 去掉其他，merge 非初审规则）
    - 3_首登到交易转化: T0 交易额（filter: 渠道类别 not in [API, 其他, 免费渠道], a_scr in [1-7]）

    返回：
    index=month, columns=[1-7全首借CPS, 1-7 T0CPS]
    """
    report_month = pd.Timestamp(meta['report_month'] + '-01')

    # ===== 1. 读取业务口径花费 =====
    df_spend = pd.read_excel(excel_path, sheet_name='2_花费')
    df_spend['date_month'] = pd.to_datetime(df_spend['date_month'])
    df_spend['业务口径花费'] = pd.to_numeric(df_spend['业务口径花费'], errors='coerce').fillna(0)

    # 过滤：去掉"其他"和"免费渠道"（与 spend_by_channel 的 filter_exclude 一致）
    df_spend_filtered = df_spend[~df_spend['渠道类别'].isin(['其他', '免费渠道'])].copy()

    # 按月聚合
    spend_monthly = df_spend_filtered.groupby('date_month')['业务口径花费'].sum()

    # ===== 2. 读取手动输入（促申完、RTA） =====
    df_manual = pd.read_excel(excel_path, sheet_name='_manual_inputs')
    manual_dict = df_manual.set_index('input_name').to_dict('index')

    # 提取月份列（排除 input_name 和可能的总计列）
    month_cols = [col for col in df_manual.columns if col not in ['input_name', '总计', 'Unnamed: 0']
                  and isinstance(col, str) and '-' in col]

    cushenwan_series = pd.Series({
        pd.Timestamp(col + '-01'): manual_dict['促申完花费'][col]
        for col in month_cols if col in manual_dict.get('促申完花费', {})
    })

    rta_series = pd.Series({
        pd.Timestamp(col + '-01'): manual_dict['RTA花费'][col]
        for col in month_cols if col in manual_dict.get('RTA花费', {})
    })

    # ===== 3. 计算总花费 =====
    total_spend = spend_monthly + cushenwan_series.reindex(spend_monthly.index, fill_value=0) + \
                  rta_series.reindex(spend_monthly.index, fill_value=0)

    # ===== 4. 读取首借交易总额 =====
    df_trade = pd.read_excel(excel_path, sheet_name='1_首借交易')
    df_trade['month'] = pd.to_datetime(df_trade['month'])
    df_trade['loan_principal_amount'] = pd.to_numeric(df_trade['loan_principal_amount'], errors='coerce').fillna(0)

    # 过滤：去掉其他
    df_trade_filtered = df_trade[~df_trade['user_group'].isin(['其他'])].copy()

    # 应用 merge_rules
    merge_rules = {'非初审-重申': '非初审', '非初审-重审及其他': '非初审'}
    df_trade_filtered['user_group'] = df_trade_filtered['user_group'].replace(merge_rules)

    # 按月聚合
    trade_monthly = df_trade_filtered.groupby('month')['loan_principal_amount'].sum()

    # ===== 5. 读取 T0 交易额 =====
    df_conversion = pd.read_excel(excel_path, sheet_name='3_首登到交易转化')
    df_conversion['date_month'] = pd.to_datetime(df_conversion['date_month'])

    # 转换 a_scr 列（处理 \N）
    df_conversion['a_scr'] = pd.to_numeric(df_conversion['a_scr'], errors='coerce')

    # 过滤条件
    # T0CPS 分母口径：仅排除 API（保留 其他、免费渠道）
    mask = (
        (df_conversion['渠道类别'] != 'API') &
        df_conversion['a_scr'].isin([1, 2, 3, 4, 5, 6, 7])
    )
    df_t0_filtered = df_conversion[mask]

    # T0 交易额
    df_t0_filtered = df_t0_filtered.copy()
    df_t0_filtered['t0_loa_amt_24h'] = pd.to_numeric(df_t0_filtered['t0_loa_amt_24h'], errors='coerce').fillna(0)
    t0_trade_monthly = df_t0_filtered.groupby('date_month')['t0_loa_amt_24h'].sum()

    # ===== 6. 计算 CPS =====
    # 对齐时间索引（取交集）
    common_index = total_spend.index.intersection(trade_monthly.index).intersection(spend_monthly.index).intersection(t0_trade_monthly.index)
    common_index = common_index[common_index <= report_month].sort_values()

    cps_all = (total_spend.reindex(common_index) / trade_monthly.reindex(common_index)).replace([np.inf, -np.inf], np.nan).fillna(0)
    cps_t0 = (spend_monthly.reindex(common_index) / t0_trade_monthly.reindex(common_index)).replace([np.inf, -np.inf], np.nan).fillna(0)

    # 构建结果
    result = pd.DataFrame({
        '1-7全首借CPS': cps_all,
        '1-7 T0CPS': cps_t0
    }, index=common_index)

    result.index.name = 'month'
    return result


def build_quality_credit_pivot(excel_path: str, meta: dict) -> pd.DataFrame:
    """
    构建质量&授信指标透视表（单表派生）。

    基于 3_首登到交易转化 表，计算：
    - 1-7 T0平均授信额度 = sum(t0_adt_amt) / sum(t0_adt_num)  [a_scr in 1-7, 渠道!=API]
    - 1-3 T0过件率 = sum(t0_adt_num) / sum(t0_ato_num)  [a_scr in 1-3, 渠道!=API, is_age_refuse='0']
    - 1-3 T0过件率_投放渠道 = 同上但 渠道 not in [API, 免费渠道]
    - 1-3 T0过件率_免费 = 同上但 渠道=='免费渠道'

    返回：
    index=month, columns=[1-7 T0平均授信额度, 1-3 T0过件率, 1-3 T0过件率_投放渠道, 1-3 T0过件率_免费]
    """
    report_month = pd.Timestamp(meta['report_month'] + '-01')

    # 读取数据
    df = pd.read_excel(excel_path, sheet_name='3_首登到交易转化')
    df['date_month'] = pd.to_datetime(df['date_month'])

    # 转换 a_scr（处理 \N）
    df['a_scr'] = pd.to_numeric(df['a_scr'], errors='coerce')

    # 转换数值列
    for col in ['t0_ato_num', 't0_adt_num', 't0_adt_amt']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # ===== 子聚合 =====

    # A1: 全渠道申完（渠道!=API, is_age_refuse='0'）
    mask_a1 = (df['渠道类别'] != 'API') & (df['is_age_refuse'].astype(str) == '0')
    a1 = df[mask_a1].groupby('date_month')['t0_ato_num'].sum()

    # A2: 投放渠道申完（渠道 not in [API, 免费渠道], is_age_refuse='0'）
    mask_a2 = (~df['渠道类别'].isin(['API', '免费渠道'])) & (df['is_age_refuse'].astype(str) == '0')
    a2 = df[mask_a2].groupby('date_month')['t0_ato_num'].sum()

    # A3: 免费渠道申完（渠道=='免费渠道', is_age_refuse='0'）
    mask_a3 = (df['渠道类别'] == '免费渠道') & (df['is_age_refuse'].astype(str) == '0')
    a3 = df[mask_a3].groupby('date_month')['t0_ato_num'].sum()

    # B1: 全渠道 1-3 授信人数（渠道!=API, a_scr in [1,2,3]）
    mask_b1 = (df['渠道类别'] != 'API') & df['a_scr'].isin([1, 2, 3])
    b1 = df[mask_b1].groupby('date_month')['t0_adt_num'].sum()

    # B2: 投放渠道 1-3 授信人数
    mask_b2 = (~df['渠道类别'].isin(['API', '免费渠道'])) & df['a_scr'].isin([1, 2, 3])
    b2 = df[mask_b2].groupby('date_month')['t0_adt_num'].sum()

    # B3: 免费渠道 1-3 授信人数
    mask_b3 = (df['渠道类别'] == '免费渠道') & df['a_scr'].isin([1, 2, 3])
    b3 = df[mask_b3].groupby('date_month')['t0_adt_num'].sum()

    # C1: 1-7 授信额度（渠道!=API, a_scr in [1-7]）
    mask_c1 = (df['渠道类别'] != 'API') & df['a_scr'].isin([1, 2, 3, 4, 5, 6, 7])
    c1 = df[mask_c1].groupby('date_month')['t0_adt_amt'].sum()

    # C2: 1-7 授信人数
    c2 = df[mask_c1].groupby('date_month')['t0_adt_num'].sum()

    # ===== 派生指标 =====
    result_dict = {}

    # 对齐索引
    all_months = pd.Index(set(a1.index) | set(a2.index) | set(a3.index) | set(b1.index) |
                          set(b2.index) | set(b3.index) | set(c1.index) | set(c2.index))
    all_months = all_months[all_months <= report_month].sort_values()

    # 过件率
    result_dict['1-3 T0过件率'] = (b1.reindex(all_months, fill_value=0) / a1.reindex(all_months, fill_value=0)).replace([np.inf, -np.inf], np.nan).fillna(0)
    result_dict['1-3 T0过件率_投放渠道'] = (b2.reindex(all_months, fill_value=0) / a2.reindex(all_months, fill_value=0)).replace([np.inf, -np.inf], np.nan).fillna(0)
    result_dict['1-3 T0过件率_免费'] = (b3.reindex(all_months, fill_value=0) / a3.reindex(all_months, fill_value=0)).replace([np.inf, -np.inf], np.nan).fillna(0)

    # 平均授信额度
    result_dict['1-7 T0平均授信额度'] = (c1.reindex(all_months, fill_value=0) / c2.reindex(all_months, fill_value=0)).replace([np.inf, -np.inf], np.nan).fillna(0)

    result = pd.DataFrame(result_dict, index=all_months)
    result.index.name = 'month'

    return result


def build_channel_overview_tencent_pivot(excel_path: str, meta: dict) -> pd.DataFrame:
    """
    构建腾讯渠道转化总览透视表（P11）。

    从 4_转化 表筛选腾讯渠道数据，计算派生指标：
    - 日耗 = business_fee / days / 10000
    - T0CPS_24h = business_fee / t0_loan_amount_24h
    - 1-7平均额度 = to_adt_credit_lmt / t0_adt_cnt
    - 进件1-3通过率 = t0_safe_adt_cnt / t0_ato_cnt_age_refuse
    - 进件1-7通过率 = t0_adt_cnt / t0_ato_cnt_age_refuse

    返回：
    index=month, columns=[日耗, T0CPS_24h, 1-7平均额度, 进件1-3通过率, 进件1-7通过率]
    """
    return _build_channel_overview_pivot(excel_path, meta, channel='腾讯')


def build_channel_overview_douyin_pivot(excel_path: str, meta: dict) -> pd.DataFrame:
    """构建抖音渠道转化总览透视表（P15）。"""
    return _build_channel_overview_pivot(excel_path, meta, channel='抖音')


def build_channel_overview_jingzhun_pivot(excel_path: str, meta: dict) -> pd.DataFrame:
    """构建精准营销渠道转化总览透视表（P19）。"""
    return _build_channel_overview_pivot(excel_path, meta, channel='精准营销')


# ── 新增: 分离的cost和quality builder函数 ──

def build_channel_overview_tencent_cost_pivot(excel_path: str, meta: dict) -> pd.DataFrame:
    """构建腾讯渠道-花费及成本图表（P11左图）。"""
    return _build_channel_overview_pivot(excel_path, meta, channel='腾讯')


def build_channel_overview_tencent_quality_pivot(excel_path: str, meta: dict) -> pd.DataFrame:
    """构建腾讯渠道-质量表现图表（P11右图）。"""
    return _build_channel_overview_pivot(excel_path, meta, channel='腾讯')


def build_channel_overview_douyin_cost_pivot(excel_path: str, meta: dict) -> pd.DataFrame:
    """构建抖音渠道-花费及成本图表（P15左图）。"""
    return _build_channel_overview_pivot(excel_path, meta, channel='抖音')


def build_channel_overview_douyin_quality_pivot(excel_path: str, meta: dict) -> pd.DataFrame:
    """构建抖音渠道-质量表现图表（P15右图）。"""
    return _build_channel_overview_pivot(excel_path, meta, channel='抖音')


def build_channel_overview_jingzhun_cost_pivot(excel_path: str, meta: dict) -> pd.DataFrame:
    """构建精准营销渠道-花费及成本图表（P19左图）。"""
    return _build_channel_overview_pivot(excel_path, meta, channel='精准营销')


def build_channel_overview_jingzhun_quality_pivot(excel_path: str, meta: dict) -> pd.DataFrame:
    """构建精准营销渠道-质量表现图表（P19右图）。"""
    return _build_channel_overview_pivot(excel_path, meta, channel='精准营销')


def _build_channel_overview_pivot(excel_path: str, meta: dict, channel: str) -> pd.DataFrame:
    """
    内部函数：构建指定渠道的转化总览。

    参数:
        excel_path: Excel文件路径
        meta: 指标配置
        channel: 渠道名称（腾讯/抖音/精准营销）
    """
    report_month = pd.Timestamp(meta['report_month'] + '-01')
    categories = meta.get('categories', [])

    # 读取 4_转化 表
    df = pd.read_excel(excel_path, sheet_name='4_转化')
    df['mon'] = pd.to_datetime(df['mon'])

    # 筛选指定渠道
    df_channel = df[df['channel'] == channel].copy()

    # 处理 \N 值：转换为 NaN
    for col in df_channel.columns:
        if df_channel[col].dtype == object:
            df_channel[col] = df_channel[col].replace(r'\N', np.nan)

    # 转换数值列
    numeric_cols = ['days', 'business_fee', 't0_loan_amount_24h', 'to_adt_credit_lmt',
                    't0_adt_cnt', 't0_safe_adt_cnt', 't0_ato_cnt_age_refuse']
    for col in numeric_cols:
        df_channel[col] = pd.to_numeric(df_channel[col], errors='coerce')

    # 按月聚合（sum）
    agg_dict = {
        'days': 'first',  # days 取第一个非空值
        'business_fee': 'sum',
        't0_loan_amount_24h': 'sum',
        'to_adt_credit_lmt': 'sum',
        't0_adt_cnt': 'sum',
        't0_safe_adt_cnt': 'sum',
        't0_ato_cnt_age_refuse': 'sum',
    }
    df_monthly = df_channel.groupby('mon').agg(agg_dict)

    # 计算所有可能的派生指标
    all_indicators = {}

    # 日耗（万元）
    all_indicators['日耗'] = (df_monthly['business_fee'] / df_monthly['days'] / 10000).replace(
        [np.inf, -np.inf], np.nan).fillna(0)

    # T0CPS_24h
    all_indicators['T0CPS_24h'] = (df_monthly['business_fee'] / df_monthly['t0_loan_amount_24h']).replace(
        [np.inf, -np.inf], np.nan).fillna(0)

    # 1-7平均额度（元）
    all_indicators['1-7平均额度'] = (df_monthly['to_adt_credit_lmt'] / df_monthly['t0_adt_cnt']).replace(
        [np.inf, -np.inf], np.nan).fillna(0)

    # 1-7额度 (与1-7平均额度相同,但列名不同)
    all_indicators['1-7额度'] = all_indicators['1-7平均额度']

    # 进件1-3通过率
    all_indicators['进件1-3通过率'] = (df_monthly['t0_safe_adt_cnt'] / df_monthly['t0_ato_cnt_age_refuse']).replace(
        [np.inf, -np.inf], np.nan).fillna(0)

    # 过件率1-3_排年龄 (与进件1-3通过率相同)
    all_indicators['过件率1-3_排年龄'] = all_indicators['进件1-3通过率']

    # 进件1-7通过率
    all_indicators['进件1-7通过率'] = (df_monthly['t0_adt_cnt'] / df_monthly['t0_ato_cnt_age_refuse']).replace(
        [np.inf, -np.inf], np.nan).fillna(0)

    # 过件率1-7_排年龄 (与进件1-7通过率相同)
    all_indicators['过件率1-7_排年龄'] = all_indicators['进件1-7通过率']

    # 根据categories筛选需要的指标
    result_dict = {}
    for cat in categories:
        if cat in all_indicators:
            result_dict[cat] = all_indicators[cat]
        else:
            # 如果找不到,警告并填充0
            print(f"Warning: indicator '{cat}' not found for channel {channel}")
            result_dict[cat] = pd.Series(0, index=df_monthly.index)

    # 构建结果
    result = pd.DataFrame(result_dict, index=df_monthly.index)
    result.index.name = 'month'

    # 截止到 report_month
    result = result.loc[result.index <= report_month].sort_index()

    return result
