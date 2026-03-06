# -*- coding: utf-8 -*-
"""Structured logging helpers."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
from pathlib import Path


class _JsonLineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "event": getattr(record, "event", "log"),
            "run_id": getattr(record, "run_id", None),
            "indicator_id": getattr(record, "indicator_id", None),
            "step": getattr(record, "step", None),
            "elapsed_ms": getattr(record, "elapsed_ms", None),
            "trace_id": getattr(record, "trace_id", None),
            "message": record.getMessage(),
        }
        return json.dumps(payload, ensure_ascii=False)


def setup_logger(run_root: Path, run_id: str, level: str = "INFO") -> logging.Logger:
    logger_name = f"report.{run_id}"
    logger = logging.getLogger(logger_name)
    logger.setLevel(level.upper())
    logger.propagate = False
    logger.handlers = []

    log_dir = run_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    json_handler = logging.FileHandler(log_dir / "run.jsonl", encoding="utf-8")
    json_handler.setFormatter(_JsonLineFormatter())
    logger.addHandler(json_handler)

    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    logger.addHandler(console)
    return logger


def log_event(logger: logging.Logger, event: str, message: str = "", **fields) -> None:
    extra = {"event": event, **fields}
    logger.info(message or event, extra=extra)

