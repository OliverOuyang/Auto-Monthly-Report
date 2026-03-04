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

    df = raw.copy()

    # 确保时间列为 datetime
    df[time_col] = pd.to_datetime(df[time_col])

    # 确保值列为数值
    df[value_col] = pd.to_numeric(df[value_col], errors='coerce').fillna(0)

    # 1. 过滤
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
