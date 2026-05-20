from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ConversationContext:
    company_name: str = ""
    stock_code: str = ""
    compare_pair: list[str] = field(default_factory=list)
    last_intent: str = ""
    last_query: str = ""
    last_resolved_query: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def context_from_state(raw: Any) -> ConversationContext:
    if not isinstance(raw, dict):
        return ConversationContext()
    compare_pair = raw.get("compare_pair")
    if not isinstance(compare_pair, list):
        compare_pair = []
    return ConversationContext(
        company_name=str(raw.get("company_name") or ""),
        stock_code=str(raw.get("stock_code") or ""),
        compare_pair=[str(item) for item in compare_pair if str(item).strip()],
        last_intent=str(raw.get("last_intent") or ""),
        last_query=str(raw.get("last_query") or ""),
        last_resolved_query=str(raw.get("last_resolved_query") or ""),
    )
