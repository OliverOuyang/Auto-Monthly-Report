# -*- coding: utf-8 -*-
"""Reusable preprocessing helpers for report builders."""

from __future__ import annotations

import numpy as np
import pandas as pd


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip() for c in out.columns]
    return out


def ensure_datetime(df: pd.DataFrame, column: str, fmt: str | None = None) -> pd.DataFrame:
    out = df.copy()
    if fmt:
        out[column] = pd.to_datetime(out[column], format=fmt, errors="coerce")
    else:
        out[column] = pd.to_datetime(out[column], errors="coerce")
    return out


def ensure_numeric(df: pd.DataFrame, columns: list[str], fillna: float = 0.0) -> pd.DataFrame:
    out = df.copy()
    for col in columns:
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(fillna)
    return out


def apply_filters(
    df: pd.DataFrame,
    include: dict[str, list] | None = None,
    exclude: dict[str, list] | None = None,
) -> pd.DataFrame:
    out = df.copy()
    include = include or {}
    exclude = exclude or {}
    for col, vals in include.items():
        out = out[out[col].isin(vals)]
    for col, vals in exclude.items():
        out = out[~out[col].isin(vals)]
    return out


def normalize_month_index(df: pd.DataFrame, column: str) -> pd.DataFrame:
    out = ensure_datetime(df, column=column)
    out[column] = out[column].dt.to_period("M").dt.to_timestamp()
    return out


def safe_divide(num: pd.Series, den: pd.Series, fillna: float = 0.0) -> pd.Series:
    result = (num / den).replace([np.inf, -np.inf], np.nan).fillna(fillna)
    return result

