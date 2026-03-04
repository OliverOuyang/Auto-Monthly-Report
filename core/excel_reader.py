# -*- coding: utf-8 -*-
"""读取 Excel 三层结构：_meta, _styles, 结构表/原数据"""

import pandas as pd
from pathlib import Path


def read_meta(excel_path: str) -> list[dict]:
    """读取 _meta sheet，每行 = 一个指标配置，返回 dict 列表。"""
    df = pd.read_excel(excel_path, sheet_name='_meta')
    meta_list = []
    for _, row in df.iterrows():
        m = row.to_dict()
        # 解析逗号分隔的 categories 为列表
        if isinstance(m.get('categories'), str):
            m['categories'] = [c.strip() for c in m['categories'].split(',')]
        # 解析 merge_rules: "A->B;C->D" → {A: B, C: D}
        if isinstance(m.get('merge_rules'), str) and m['merge_rules']:
            rules = {}
            for rule in m['merge_rules'].split(';'):
                parts = rule.strip().split('->')
                if len(parts) == 2:
                    rules[parts[0].strip()] = parts[1].strip()
            m['merge_rules'] = rules
        else:
            m['merge_rules'] = {}
        # 解析 filter_exclude 为列表
        if isinstance(m.get('filter_exclude'), str):
            m['filter_exclude'] = [v.strip() for v in m['filter_exclude'].split(',')]
        else:
            m['filter_exclude'] = []
        # 确保 show_total_line 是 bool
        m['show_total_line'] = bool(m.get('show_total_line', True))
        # 确保 unit_divisor 是数值
        m['unit_divisor'] = float(m.get('unit_divisor', 1))
        # slide_order
        m['slide_order'] = int(m.get('slide_order', 999))
        meta_list.append(m)
    return meta_list


def read_styles(excel_path: str) -> dict:
    """读取 _styles sheet，返回 {'colors': {name: hex}, 'global': {key: value}}。"""
    df = pd.read_excel(excel_path, sheet_name='_styles')

    colors = {}
    globals_ = {}

    # 分类颜色区域：有 role 列的行
    for _, row in df.iterrows():
        key = row.get('style_key')
        if pd.isna(key) or key == 'key':
            continue
        hex_color = row.get('hex_color')
        role = row.get('role')
        if pd.notna(role):
            colors[key] = hex_color
        elif pd.notna(hex_color):
            # 全局样式区域（key 列在 style_key, value 在 hex_color）
            globals_[key] = hex_color

    # 全局样式也可能在后续行（通过 openpyxl 写入时 key/value 在 col1/col2）
    # 尝试读取更多行
    try:
        df_full = pd.read_excel(excel_path, sheet_name='_styles', header=None)
        for _, row in df_full.iterrows():
            if row.iloc[0] == 'key' and row.iloc[1] == 'value':
                continue
            if row.iloc[0] in ('style_key',):
                continue
            # 检查是否已在 colors 中
            k = row.iloc[0]
            if pd.notna(k) and k not in colors:
                v = row.iloc[1]
                if pd.notna(v) and str(k) not in ('style_key', 'key'):
                    # 如果第三列(role)为空，则视为全局样式
                    role_val = row.iloc[2] if len(row) > 2 else None
                    if pd.isna(role_val):
                        globals_[str(k)] = str(v)
    except Exception:
        pass

    return {
        'colors': colors,
        'global': globals_,
    }


def read_pivot(excel_path: str, indicator_id: str) -> pd.DataFrame | None:
    """读取结构表 sheet。返回 DataFrame（month 为 index），找不到返回 None。"""
    try:
        df = pd.read_excel(excel_path, sheet_name=indicator_id)
    except ValueError:
        return None
    if 'month' not in df.columns:
        return None
    df['month'] = pd.to_datetime(df['month'], format='mixed')
    df = df.set_index('month').sort_index()
    return df


def read_raw(excel_path: str, sheet_name: str) -> pd.DataFrame:
    """读取原数据 sheet。"""
    df = pd.read_excel(excel_path, sheet_name=sheet_name)
    return df
