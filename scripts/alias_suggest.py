from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FAILED_CASES = ROOT / "eval" / "failed_cases.csv"
ALIASES = ROOT / "eval" / "company_aliases.csv"


def _load_existing_aliases() -> set[str]:
    if not ALIASES.exists():
        return set()
    aliases: set[str] = set()
    with ALIASES.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            alias = str(row.get("alias") or "").strip().lower()
            if alias:
                aliases.add(alias)
    return aliases


def _candidate_tokens(query: str) -> list[str]:
    tokens: list[str] = []
    text = str(query or "").strip()
    text = re.sub(r"[，。？！,.!?]", " ", text)
    parts = re.split(r"(?:和|与|vs|VS|比较|对比)", text)
    stop_pattern = r"(利润|营收|收入|现金流|趋势|匹配|说明|为什么|如何|怎么看|财报|更好|更稳|哪个|谁|吗|呢|啊)"
    for raw in parts:
        part = re.sub(stop_pattern, "", raw).strip()
        part = re.sub(r"\s+", "", part)
        if re.fullmatch(r"[\u4e00-\u9fff]{2,8}", part):
            tokens.append(part)
    joined = "".join(parts)
    for code in re.findall(r"\b\d{6}\b", joined):
        tokens.append(code)
    return list(dict.fromkeys(tokens))


def main() -> None:
    if not FAILED_CASES.exists():
        print("No failed_cases.csv found.")
        return

    existing = _load_existing_aliases()
    suggestions: list[tuple[str, str, str]] = []
    with FAILED_CASES.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            query = str(row.get("query") or "")
            fail_reason = str(row.get("fail_reason") or "")
            for token in _candidate_tokens(query):
                if token.lower() in existing:
                    continue
                suggestions.append((token, "", fail_reason))

    if not suggestions:
        print("No new alias suggestions from failed cases.")
        return

    print("=== Alias Suggestions (from failed_cases.csv) ===")
    print("alias,canonical,from_fail_reason")
    seen: set[str] = set()
    for alias, canonical, reason in suggestions:
        key = alias.lower()
        if key in seen:
            continue
        seen.add(key)
        print(f"{alias},{canonical},{reason}")


if __name__ == "__main__":
    main()
