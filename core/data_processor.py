# -*- coding: utf-8 -*-
"""按 meta 规则从 raw data 构建结构表（透视表）"""

import pandas as pd
import numpy as np


def _apply_period(df: pd.DataFrame, meta: dict) -> pd.DataFrame:
    report_month = pd.Timestamp(meta['report_month'] + '-01')
    out = df.loc[df.index <= report_month]
    start_month = meta.get('start_month')
    if start_month:
        out = out.loc[out.index >= pd.Timestamp(str(start_month) + '-01')]
    return out.sort_index()


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

    # 4. 期间过滤（含 start_month 可选）
    pivot = _apply_period(pivot, meta)

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

    def _normalize_name(v) -> str:
        return str(v).replace('\u3000', ' ').strip().replace(' ', '').lower()

    def _extract_month_cols(df_manual: pd.DataFrame) -> list[str]:
        cols: list[str] = []
        for col in df_manual.columns:
            if col in ['input_name', '总计', 'Unnamed: 0']:
                continue
            if isinstance(col, (pd.Timestamp, np.datetime64)):
                cols.append(str(pd.Timestamp(col).strftime('%Y-%m')))
                continue
            col_text = str(col).strip()
            if '-' in col_text:
                cols.append(col_text[:7])
        # 去重保序
        seen = set()
        out = []
        for c in cols:
            if c not in seen:
                seen.add(c)
                out.append(c)
        return out

    def _extract_manual_series(df_manual: pd.DataFrame, target_tokens: list[str]) -> pd.Series:
        if df_manual is None or df_manual.empty or 'input_name' not in df_manual.columns:
            return pd.Series(dtype=float)

        tmp = df_manual.copy()
        tmp['__name_norm__'] = tmp['input_name'].map(_normalize_name)

        def _match_target(name_norm: str) -> bool:
            return all(tok in name_norm for tok in target_tokens)

        matched = tmp[tmp['__name_norm__'].map(_match_target)]
        if matched.empty:
            return pd.Series(dtype=float)

        row = matched.iloc[0]
        month_cols = _extract_month_cols(tmp)
        values = {}
        for month_col in month_cols:
            if month_col not in row.index:
                continue
            values[pd.Timestamp(month_col + '-01')] = pd.to_numeric(row[month_col], errors='coerce')
        s = pd.Series(values, dtype=float).fillna(0.0)
        return s

    def _load_manual_inputs_df() -> pd.DataFrame:
        try:
            return pd.read_excel(excel_path, sheet_name='_manual_inputs')
        except ValueError:
            csv_path = meta.get('manual_inputs_csv')
            if csv_path:
                try:
                    return pd.read_csv(csv_path, encoding='utf-8-sig')
                except FileNotFoundError:
                    return pd.DataFrame()
            return pd.DataFrame()

    # ===== 2. 读取手动输入（促申完、RTA） =====
    df_manual = _load_manual_inputs_df()
    cushenwan_series = _extract_manual_series(df_manual, ['促申完', '花费'])
    rta_series = _extract_manual_series(df_manual, ['rta', '花费'])

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
    return _apply_period(result, meta)


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

    # 期间过滤（含 start_month 可选）
    result = _apply_period(result, meta)

    return result


# ============================================================================
# 抖音渠道数据处理函数 (P16-18)
# ============================================================================

def build_douyin_request_pivot(excel_path: str, meta: dict) -> pd.DataFrame:
    """构建抖音请求及参竞透视表(P16) - 日请求量 + 参��率"""
    report_month = pd.Timestamp(meta['report_month'] + '-01')
    df = pd.read_excel(excel_path, sheet_name='6_抖音')
    df['mon'] = pd.to_datetime(df['mon'])
    df = df.replace('\\N', np.nan)

    numeric_cols = ['req_cnt', 'cj_cnt']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    df_monthly = df.groupby('mon').agg({
        'req_cnt': 'sum',
        'cj_cnt': 'sum'
    }).reset_index()
    df_monthly.set_index('mon', inplace=True)

    all_indicators = {}
    df_monthly['days_in_month'] = df_monthly.index.to_series().apply(lambda x: x.days_in_month)
    # 日请求量（亿）
    all_indicators['日请求量'] = (df_monthly['req_cnt'] / 100000000 / df_monthly['days_in_month'])
    # 参竞率 = cj_cnt / req_cnt
    all_indicators['参竞率'] = (df_monthly['cj_cnt'] / df_monthly['req_cnt']).replace([np.inf, -np.inf], np.nan).fillna(0)

    result = pd.DataFrame(all_indicators, index=df_monthly.index)
    result.index.name = 'month'
    result = _apply_period(result, meta)

    # 自动剔除参竞率为0的月份（无效数据）
    if '参竞率' in result.columns:
        result = result[result['参竞率'] > 0]

    return result


def build_douyin_win_rate_pivot(excel_path: str, meta: dict) -> pd.DataFrame:
    """构建抖音竞得率透视表(P17) - 整体 + 按v8prea分组(1Q/2Q/3Q/UNK)"""
    report_month = pd.Timestamp(meta['report_month'] + '-01')
    categories = meta.get('categories', [])
    df = pd.read_excel(excel_path, sheet_name='6_抖音')
    df['mon'] = pd.to_datetime(df['mon'])
    df = df.replace('\\N', np.nan)

    numeric_cols = ['cj_cnt', 'exp_cnt']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    df_overall = df.groupby('mon').agg({'cj_cnt': 'sum', 'exp_cnt': 'sum'}).reset_index()
    df_overall.set_index('mon', inplace=True)

    all_indicators = {}
    all_indicators['整体竞得率'] = (df_overall['exp_cnt'] / df_overall['cj_cnt']).replace([np.inf, -np.inf], np.nan).fillna(0)

    if 'v8prea' in df.columns:
        for group_name in ['1Q', '2Q', '3Q', 'UNK']:
            group_key = f'{group_name}竞得率'
            if group_key in categories:
                if group_name == 'UNK':
                    df_group = df[df['v8prea'].isna() | (df['v8prea'] == 'UNK')]
                else:
                    df_group = df[df['v8prea'] == group_name]

                df_group_monthly = df_group.groupby('mon').agg({'cj_cnt': 'sum', 'exp_cnt': 'sum'}).reset_index()
                df_group_monthly.set_index('mon', inplace=True)
                all_indicators[group_key] = (df_group_monthly['exp_cnt'] / df_group_monthly['cj_cnt']).replace([np.inf, -np.inf], np.nan).fillna(0).reindex(df_overall.index, fill_value=0)

    result = pd.DataFrame(all_indicators, index=df_overall.index)
    result.index.name = 'month'
    result = _apply_period(result, meta)

    # 自动剔除整体竞得率为0的月份（无效数据）
    if '整体竞得率' in result.columns:
        result = result[result['整体竞得率'] > 0]

    return result


def build_douyin_conversion_pivot(excel_path: str, meta: dict) -> pd.DataFrame:
    """构建抖音曝光至授信转化透视表(P18) - 曝光-授信率*1000 + CTR + CVR"""
    report_month = pd.Timestamp(meta['report_month'] + '-01')
    df = pd.read_excel(excel_path, sheet_name='6_抖音')
    df['mon'] = pd.to_datetime(df['mon'])
    df = df.replace('\\N', np.nan)

    numeric_cols = ['exp_cnt', 'clk_cnt', 't0_adt_cnt']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    df_monthly = df.groupby('mon').agg({
        'exp_cnt': 'sum',
        'clk_cnt': 'sum',
        't0_adt_cnt': 'sum'
    }).reset_index()
    df_monthly.set_index('mon', inplace=True)

    all_indicators = {}
    # 曝光-授信率 = t0_adt_cnt / exp_cnt * 1000
    all_indicators['曝光-授信'] = (df_monthly['t0_adt_cnt'] / df_monthly['exp_cnt'] * 1000).replace([np.inf, -np.inf], np.nan).fillna(0)
    # CTR = clk_cnt / exp_cnt
    all_indicators['CTR'] = (df_monthly['clk_cnt'] / df_monthly['exp_cnt']).replace([np.inf, -np.inf], np.nan).fillna(0)
    # CVR = t0_adt_cnt / clk_cnt
    all_indicators['CVR'] = (df_monthly['t0_adt_cnt'] / df_monthly['clk_cnt']).replace([np.inf, -np.inf], np.nan).fillna(0)

    result = pd.DataFrame(all_indicators, index=df_monthly.index)
    result.index.name = 'month'
    result = _apply_period(result, meta)
    return result

# ============================================================================
# 抖音渠道左右分图包装函数
# ============================================================================

def build_douyin_win_rate_overall_pivot(excel_path: str, meta: dict) -> pd.DataFrame:
    """P17左图：抖音整体竞得率"""
    full_pivot = build_douyin_win_rate_pivot(excel_path, meta)
    return full_pivot[['整体竞得率']]


def build_douyin_win_rate_grouped_pivot(excel_path: str, meta: dict) -> pd.DataFrame:
    """P17右图：抖音分组竞得率(1Q/2Q/3Q/UNK)"""
    full_pivot = build_douyin_win_rate_pivot(excel_path, meta)
    grouped_cols = [col for col in full_pivot.columns if col != '整体竞得率']
    return full_pivot[grouped_cols]


def build_douyin_conversion_overall_pivot(excel_path: str, meta: dict) -> pd.DataFrame:
    """P18左图：抖音曝光-授信率*1000"""
    full_pivot = build_douyin_conversion_pivot(excel_path, meta)
    return full_pivot[['曝光-授信']]


def build_douyin_conversion_funnel_pivot(excel_path: str, meta: dict) -> pd.DataFrame:
    """P18右图：抖音分环节转化(CTR+CVR)"""
    full_pivot = build_douyin_conversion_pivot(excel_path, meta)
    return full_pivot[['CTR', 'CVR']]


def _pick_col(df: pd.DataFrame, candidates: list[str]) -> str:
    for name in candidates:
        if name in df.columns:
            return name
    raise KeyError(f"None of columns found: {candidates}")


def _safe_ratio(numer: pd.Series, denom: pd.Series, scale: float = 1.0) -> pd.Series:
    return (numer / denom * scale).replace([np.inf, -np.inf], np.nan).fillna(0)


# ============================================================================
# 腾讯渠道数据处理函数 (P12-14)
# ============================================================================

def build_tencent_request_pivot(excel_path: str, meta: dict) -> pd.DataFrame:
    report_month = pd.Timestamp(meta['report_month'] + '-01')
    df = pd.read_excel(excel_path, sheet_name='5_腾讯').replace('\\N', np.nan)
    df['mon'] = pd.to_datetime(df['mon'])

    request_col = _pick_col(df, ['cnt_request', 'req_cnt'])
    participate_col = _pick_col(df, ['cnt_request_yes', 'cj_cnt'])
    for col in [request_col, participate_col]:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    monthly = df.groupby('mon')[[request_col, participate_col]].sum()
    daily_request = monthly[request_col] / monthly.index.to_series().dt.days_in_month / 100000000 / 2
    participate_rate = _safe_ratio(monthly[participate_col], monthly[request_col])

    result = pd.DataFrame({
        '日请求量': daily_request,
        '参竞率': participate_rate,
    }, index=monthly.index)
    result.index.name = 'month'
    return _apply_period(result, meta)


def build_tencent_win_rate_pivot(excel_path: str, meta: dict) -> pd.DataFrame:
    report_month = pd.Timestamp(meta['report_month'] + '-01')
    categories = meta.get('categories', [])
    df = pd.read_excel(excel_path, sheet_name='5_腾讯').replace('\\N', np.nan)
    df['mon'] = pd.to_datetime(df['mon'])

    group_col = _pick_col(df, ['v7prea', 'v8prea'])
    participate_col = _pick_col(df, ['cnt_request_yes', 'cj_cnt'])
    win_col = _pick_col(df, ['cnt_exposure', 'exp_cnt'])
    for col in [participate_col, win_col]:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    overall = df.groupby('mon')[[participate_col, win_col]].sum()
    result_dict = {'整体竞得率': _safe_ratio(overall[win_col], overall[participate_col], scale=2)}

    for group_name in ['1Q', '2Q', '3Q', 'UNK']:
        key = f'{group_name}竞得率'
        if key not in categories:
            continue
        if group_name == 'UNK':
            df_group = df[df[group_col].isna() | (df[group_col] == 'UNK')]
        else:
            df_group = df[df[group_col] == group_name]
        grouped = df_group.groupby('mon')[[participate_col, win_col]].sum()
        result_dict[key] = _safe_ratio(
            grouped[win_col], grouped[participate_col], scale=2
        ).reindex(overall.index, fill_value=0)

    result = pd.DataFrame(result_dict, index=overall.index)
    result.index.name = 'month'
    result = _apply_period(result, meta)
    if '整体竞得率' in result.columns:
        result = result[result['整体竞得率'] > 0]
    return result


def build_tencent_conversion_pivot(excel_path: str, meta: dict) -> pd.DataFrame:
    report_month = pd.Timestamp(meta['report_month'] + '-01')
    df = pd.read_excel(excel_path, sheet_name='5_腾讯').replace('\\N', np.nan)
    df['mon'] = pd.to_datetime(df['mon'])

    exposure_col = _pick_col(df, ['cnt_exposure', 'exp_cnt'])
    click_col = _pick_col(df, ['cnt_click', 'clk_cnt'])
    adt_col = _pick_col(df, ['cnt_adt_t0', 't0_adt_cnt'])
    for col in [exposure_col, click_col, adt_col]:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    monthly = df.groupby('mon')[[exposure_col, click_col, adt_col]].sum()
    result = pd.DataFrame({
        '曝光-授信': _safe_ratio(monthly[adt_col], monthly[exposure_col], scale=1000),
        'CTR': _safe_ratio(monthly[click_col], monthly[exposure_col]),
        'CVR': _safe_ratio(monthly[adt_col], monthly[click_col]),
    }, index=monthly.index)
    result.index.name = 'month'
    return _apply_period(result, meta)


def build_tencent_win_rate_overall_pivot(excel_path: str, meta: dict) -> pd.DataFrame:
    full_pivot = build_tencent_win_rate_pivot(excel_path, meta)
    return full_pivot[['整体竞得率']]


def build_tencent_win_rate_grouped_pivot(excel_path: str, meta: dict) -> pd.DataFrame:
    full_pivot = build_tencent_win_rate_pivot(excel_path, meta)
    grouped_cols = [col for col in full_pivot.columns if col != '整体竞得率']
    return full_pivot[grouped_cols]


def build_tencent_conversion_overall_pivot(excel_path: str, meta: dict) -> pd.DataFrame:
    full_pivot = build_tencent_conversion_pivot(excel_path, meta)
    return full_pivot[['曝光-授信']]


def build_tencent_conversion_funnel_pivot(excel_path: str, meta: dict) -> pd.DataFrame:
    full_pivot = build_tencent_conversion_pivot(excel_path, meta)
    return full_pivot[['CTR', 'CVR']]


# ============================================================================
# 精准渠道数据处理函数 (P20-21)
# ============================================================================

def build_jingzhun_attack_result_pivot(excel_path: str, meta: dict) -> pd.DataFrame:
    report_month = pd.Timestamp(meta['report_month'] + '-01')
    df = pd.read_excel(excel_path, sheet_name='7_精准').replace('\\N', np.nan)
    df['mon'] = pd.to_datetime(df['mon'])

    attack_col = _pick_col(df, ['force_attack_count', 'attack_cnt'])
    allowed_col = _pick_col(df, ['allowed_cnt', 'allowed_count'])
    for col in [attack_col, allowed_col]:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    monthly = df.groupby('mon')[[attack_col, allowed_col]].sum()
    days = monthly.index.to_series().dt.days_in_month
    result = pd.DataFrame({
        '日均撞库量（亿）': monthly[attack_col] / 100000000 / days,
        '日均可营销量（亿）': monthly[allowed_col] / 100000000 / days,
        '可营销率': _safe_ratio(monthly[allowed_col], monthly[attack_col]),
    }, index=monthly.index)
    result.index.name = 'month'
    return _apply_period(result, meta)


def build_jingzhun_conversion_pivot(excel_path: str, meta: dict) -> pd.DataFrame:
    report_month = pd.Timestamp(meta['report_month'] + '-01')
    df_jingzhun = pd.read_excel(excel_path, sheet_name='7_精准').replace('\\N', np.nan)
    df_jingzhun['mon'] = pd.to_datetime(df_jingzhun['mon'])
    allowed_col = _pick_col(df_jingzhun, ['allowed_cnt', 'allowed_count'])
    df_jingzhun[allowed_col] = pd.to_numeric(df_jingzhun[allowed_col], errors='coerce').fillna(0)
    allowed_series = df_jingzhun.groupby('mon')[allowed_col].sum()

    df_conv = pd.read_excel(excel_path, sheet_name='4_转化').replace('\\N', np.nan)
    df_conv['mon'] = pd.to_datetime(df_conv['mon'])
    channel_col = _pick_col(df_conv, ['channel', '渠道类别'])
    login_col = _pick_col(df_conv, ['login_cnt'])
    adt_col = _pick_col(df_conv, ['t0_adt_cnt'])
    for col in [login_col, adt_col]:
        df_conv[col] = pd.to_numeric(df_conv[col], errors='coerce').fillna(0)

    df_conv = df_conv[df_conv[channel_col] == '精准营销']
    conv_monthly = df_conv.groupby('mon')[[login_col, adt_col]].sum()
    conv_monthly = conv_monthly.reindex(allowed_series.index, fill_value=0)

    result = pd.DataFrame(
        {
            '千次可营销-授信率': _safe_ratio(conv_monthly[adt_col], allowed_series, scale=1000),
            '千次可营销-首登率': _safe_ratio(conv_monthly[login_col], allowed_series, scale=1000),
            '首登-授信率': _safe_ratio(conv_monthly[adt_col], conv_monthly[login_col]),
        },
        index=allowed_series.index,
    )
    result.index.name = 'month'
    return _apply_period(result, meta)


def build_jingzhun_conversion_overall_pivot(excel_path: str, meta: dict) -> pd.DataFrame:
    # 为左图输出完整口径，便于分析模板拿到分环节指标补充结论文本。
    return build_jingzhun_conversion_pivot(excel_path, meta)


def build_jingzhun_conversion_funnel_pivot(excel_path: str, meta: dict) -> pd.DataFrame:
    full_pivot = build_jingzhun_conversion_pivot(excel_path, meta)
    return full_pivot[['千次可营销-首登率', '首登-授信率']]


INDICATOR_BUILDERS = {
    "cps_all_channel": build_cps_all_channel_pivot,
    "quality_credit": build_quality_credit_pivot,
    "channel_overview_tencent_cost": build_channel_overview_tencent_cost_pivot,
    "channel_overview_tencent_quality": build_channel_overview_tencent_quality_pivot,
    "channel_overview_douyin_cost": build_channel_overview_douyin_cost_pivot,
    "channel_overview_douyin_quality": build_channel_overview_douyin_quality_pivot,
    "channel_overview_jingzhun_cost": build_channel_overview_jingzhun_cost_pivot,
    "channel_overview_jingzhun_quality": build_channel_overview_jingzhun_quality_pivot,
    "tencent_request": build_tencent_request_pivot,
    "tencent_win_rate_overall": build_tencent_win_rate_overall_pivot,
    "tencent_win_rate_grouped": build_tencent_win_rate_grouped_pivot,
    "tencent_conversion_overall": build_tencent_conversion_overall_pivot,
    "tencent_conversion_funnel": build_tencent_conversion_funnel_pivot,
    "douyin_request": build_douyin_request_pivot,
    "douyin_win_rate_overall": build_douyin_win_rate_overall_pivot,
    "douyin_win_rate_grouped": build_douyin_win_rate_grouped_pivot,
    "douyin_conversion_overall": build_douyin_conversion_overall_pivot,
    "douyin_conversion_funnel": build_douyin_conversion_funnel_pivot,
    "jingzhun_attack_result": build_jingzhun_attack_result_pivot,
    "jingzhun_conversion": build_jingzhun_conversion_pivot,
    "jingzhun_conversion_overall": build_jingzhun_conversion_overall_pivot,
    "jingzhun_conversion_funnel": build_jingzhun_conversion_funnel_pivot,
}


def get_indicator_builder(indicator_id: str):
    return INDICATOR_BUILDERS.get(indicator_id)
