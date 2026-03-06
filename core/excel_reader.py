# -*- coding: utf-8 -*-
"""Read report metadata, style config, and raw/pivot sheets from Excel/profile."""

from __future__ import annotations

from pathlib import Path
import json

import pandas as pd
import yaml


def _as_bool(v, default: bool = False) -> bool:
    if v is None:
        return default
    if isinstance(v, float) and pd.isna(v):
        return default
    if isinstance(v, str):
        s = v.strip().lower()
        if s in {"true", "1", "yes", "y"}:
            return True
        if s in {"false", "0", "no", "n", ""}:
            return False
    return bool(v)


def _normalize_meta_record(record: dict) -> dict:
    m = dict(record)

    if isinstance(m.get("categories"), str):
        m["categories"] = [c.strip() for c in m["categories"].split(",") if c.strip()]

    merge_rules = m.get("merge_rules")
    if isinstance(merge_rules, str) and merge_rules:
        rules = {}
        for rule in merge_rules.split(";"):
            parts = rule.strip().split("->")
            if len(parts) == 2:
                rules[parts[0].strip()] = parts[1].strip()
        m["merge_rules"] = rules
    elif not isinstance(merge_rules, dict):
        m["merge_rules"] = {}

    filter_exclude = m.get("filter_exclude")
    if isinstance(filter_exclude, str):
        m["filter_exclude"] = [v.strip() for v in filter_exclude.split(",") if v.strip()]
    elif filter_exclude is None:
        m["filter_exclude"] = []

    # Optional advanced config fields can be serialized as JSON strings in Excel _meta.
    strategy_annotations = m.get("strategy_annotations")
    if strategy_annotations is None or (
        isinstance(strategy_annotations, float) and pd.isna(strategy_annotations)
    ):
        m["strategy_annotations"] = []
        strategy_annotations = m["strategy_annotations"]
    if isinstance(strategy_annotations, str) and strategy_annotations.strip():
        txt = strategy_annotations.strip()
        if txt.startswith("[") or txt.startswith("{"):
            try:
                m["strategy_annotations"] = json.loads(txt)
            except json.JSONDecodeError:
                # Keep original string if not valid JSON.
                pass

    m["show_total_line"] = _as_bool(m.get("show_total_line", True), default=True)
    m["is_left_chart"] = _as_bool(m.get("is_left_chart", False), default=False)
    m["is_right_chart"] = _as_bool(m.get("is_right_chart", False), default=False)
    m["merge_with_prev"] = _as_bool(m.get("merge_with_prev", False), default=False)
    m["use_llm_analysis"] = _as_bool(m.get("use_llm_analysis", False), default=False)
    m["unit_divisor"] = float(m.get("unit_divisor", 1))
    m["slide_order"] = int(m.get("slide_order", 999))
    return m


def _load_profile(profile_path: str) -> dict:
    with open(profile_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def read_meta(excel_path: str) -> list[dict]:
    """Read meta rows from Excel _meta sheet."""
    df = pd.read_excel(excel_path, sheet_name="_meta")
    return [_normalize_meta_record(row.to_dict()) for _, row in df.iterrows()]


def read_meta_from_profile(profile_path: str) -> list[dict]:
    """Read indicator meta from external YAML profile."""
    cfg = _load_profile(profile_path)
    report_month = cfg.get("report_month")
    manual_inputs_csv = cfg.get("manual_inputs_csv")
    indicators = cfg.get("indicators", []) or []

    meta_list: list[dict] = []
    for indicator in indicators:
        rec = dict(indicator)
        if report_month and not rec.get("report_month"):
            rec["report_month"] = report_month
        if manual_inputs_csv:
            rec["manual_inputs_csv"] = manual_inputs_csv
        meta_list.append(_normalize_meta_record(rec))
    return meta_list


def read_styles(excel_path: str) -> dict:
    """Read style config from Excel _styles sheet."""
    df = pd.read_excel(excel_path, sheet_name="_styles")

    colors = {}
    global_styles = {}

    for _, row in df.iterrows():
        key = row.get("style_key")
        if pd.isna(key) or key == "key":
            continue
        hex_color = row.get("hex_color")
        role = row.get("role")
        if pd.notna(role):
            colors[str(key)] = str(hex_color)
        elif pd.notna(hex_color):
            global_styles[str(key)] = str(hex_color)

    try:
        df_full = pd.read_excel(excel_path, sheet_name="_styles", header=None)
        for _, row in df_full.iterrows():
            if row.iloc[0] == "key" and row.iloc[1] == "value":
                continue
            if row.iloc[0] in ("style_key",):
                continue
            k = row.iloc[0]
            if pd.notna(k) and k not in colors:
                v = row.iloc[1]
                if pd.notna(v) and str(k) not in ("style_key", "key"):
                    role_val = row.iloc[2] if len(row) > 2 else None
                    if pd.isna(role_val):
                        global_styles[str(k)] = str(v)
    except Exception:
        pass

    return {"colors": colors, "global": global_styles}


def read_styles_from_profile(profile_path: str) -> dict:
    """Read style config from external YAML profile."""
    cfg = _load_profile(profile_path)
    styles = cfg.get("styles", {}) or {}
    colors = styles.get("colors", {}) or {}
    global_styles = styles.get("global", {}) or {}
    return {"colors": colors, "global": global_styles}


def read_pivot(excel_path: str, indicator_id: str) -> pd.DataFrame | None:
    """Read pivot sheet by indicator_id. Return None if not found."""
    try:
        df = pd.read_excel(excel_path, sheet_name=indicator_id)
    except ValueError:
        return None
    if "month" not in df.columns:
        return None
    df["month"] = pd.to_datetime(df["month"], format="mixed")
    return df.set_index("month").sort_index()


def read_raw(excel_path: str, sheet_name: str) -> pd.DataFrame:
    """Read raw sheet by name."""
    return pd.read_excel(excel_path, sheet_name=sheet_name)


def read_manual_inputs(excel_path: str) -> pd.DataFrame:
    """Read _manual_inputs sheet if present, otherwise return empty DataFrame."""
    try:
        return pd.read_excel(excel_path, sheet_name="_manual_inputs")
    except ValueError:
        return pd.DataFrame()
