from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class Scores:
    profitability: float
    cash_saving: float
    future_potential: float


@dataclass
class AnalysisResult:
    plain_cashflow_summary: str
    future_outlook: str
    scores: Scores
    sentiment_label: str
    risk_notes: str
    ai_status: str

    def to_public_dict(self) -> dict:
        return asdict(self)
