# -*- coding: utf-8 -*-
"""Profile/meta schema validation helpers."""

from __future__ import annotations


def validate_indicator_meta(meta: dict, row_idx: int) -> list[str]:
    errors: list[str] = []

    required_fields = ("indicator_id", "chart_type", "slide_order", "categories")
    missing = [f for f in required_fields if meta.get(f) in (None, "")]
    if missing:
        errors.append(f"Row {row_idx}: missing required fields: {', '.join(missing)}")
        return errors

    categories = meta.get("categories")
    if not isinstance(categories, list) or not categories:
        errors.append(f"Row {row_idx}: categories must be a non-empty list")

    try:
        int(meta.get("slide_order"))
    except (TypeError, ValueError):
        errors.append(f"Row {row_idx}: slide_order must be an integer")

    data_source_type = str(meta.get("data_source_type", "single")).strip()
    if data_source_type not in {"single", "derived"}:
        errors.append(f"Row {row_idx}: data_source_type must be single/derived")

    if data_source_type == "single":
        if not meta.get("raw_sheet"):
            errors.append(f"Row {row_idx}: single source indicator requires raw_sheet")

    return errors


def validate_meta_list(meta_list: list[dict]) -> list[str]:
    errors: list[str] = []
    for idx, meta in enumerate(meta_list, start=1):
        errors.extend(validate_indicator_meta(meta, idx))
    return errors
