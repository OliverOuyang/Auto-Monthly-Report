# -*- coding: utf-8 -*-
"""Simple disk cache for expensive report steps."""

from __future__ import annotations

import hashlib
import pickle
from pathlib import Path
from typing import Callable, TypeVar

T = TypeVar("T")


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


class DiskCache:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, namespace: str, key: str) -> Path:
        ns = self.root / namespace
        ns.mkdir(parents=True, exist_ok=True)
        return ns / f"{_hash_key(key)}.pkl"

    def get_or_compute(self, namespace: str, key: str, compute_fn: Callable[[], T]) -> T:
        p = self._path(namespace, key)
        if p.exists():
            with p.open("rb") as f:
                return pickle.load(f)
        value = compute_fn()
        with p.open("wb") as f:
            pickle.dump(value, f)
        return value

