from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

DEFAULT_ALIAS_TO_CANONICAL: dict[str, str] = {
    "贵州茅台": "贵州茅台",
    "茅台": "贵州茅台",
    "600519": "600519",
    "宁德时代": "宁德时代",
    "宁德": "宁德时代",
    "300750": "300750",
    "比亚迪": "比亚迪",
    "002594": "002594",
    "平安银行": "平安银行",
    "000001": "000001",
    "招商银行": "招商银行",
    "600036": "600036",
    "万科": "万科A",
    "万科a": "万科A",
    "000002": "000002",
    "格力": "格力电器",
    "格力电器": "格力电器",
    "000651": "000651",
}


def _csv_path() -> Path:
    return Path(__file__).resolve().parents[1] / "eval" / "company_aliases.csv"


@lru_cache(maxsize=1)
def _load_aliases_cached() -> dict[str, str]:
    path = _csv_path()
    if not path.exists():
        return dict(DEFAULT_ALIAS_TO_CANONICAL)

    mapping: dict[str, str] = {}
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                alias = str(row.get("alias") or "").strip().lower()
                canonical = str(row.get("canonical") or "").strip()
                if alias and canonical:
                    mapping[alias] = canonical
    except Exception:
        return dict(DEFAULT_ALIAS_TO_CANONICAL)

    if not mapping:
        return dict(DEFAULT_ALIAS_TO_CANONICAL)
    return mapping


def load_aliases(*, force_reload: bool = False) -> dict[str, str]:
    if force_reload:
        _load_aliases_cached.cache_clear()
    return _load_aliases_cached()
