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


@dataclass
class AgentStep:
    step_name: str
    status: str
    summary: str
    tool_name: str = ""
    error: str = ""


@dataclass
class ToolCallResult:
    tool_name: str
    success: bool
    summary: str
    error: str = ""


@dataclass
class EvaluationResult:
    has_risk_note: bool
    has_data_source: bool
    has_forbidden_advice: bool
    explains_core_metrics: bool
    quality_score: int
    notes: list[str]


@dataclass
class AgentResult:
    query: str
    resolved_query: str
    intent: str
    steps: list[AgentStep]
    tool_calls: list[ToolCallResult]
    analysis: AnalysisResult | None
    snapshot: dict
    warnings: list[str]
    data_quality: dict
    evaluation: EvaluationResult | None
    comparison: dict | None
    suggested_questions: list[str]
    context_used: bool = False
    context_company_name: str = ""
    context_stock_code: str = ""
