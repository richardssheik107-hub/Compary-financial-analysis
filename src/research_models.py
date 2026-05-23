from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class SourceNote:
    source_type: str
    title: str
    detail: str = ""
    file_path: str = ""


@dataclass
class ResearchDocument:
    title: str
    source_type: str
    content: str
    file_path: str


@dataclass
class CompanyResearchContext:
    company_name: str
    stock_code: str
    company_profile: str
    financial_metrics: dict
    business_segments: list[str] = field(default_factory=list)
    management_discussion: list[str] = field(default_factory=list)
    research_views: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    source_notes: list[SourceNote] = field(default_factory=list)
    data_quality: dict = field(default_factory=dict)
    source_summary: dict = field(default_factory=dict)


@dataclass
class ResearchResult:
    report_type: str
    title: str
    one_line_conclusion: str
    business_overview: str
    operating_performance: str
    profitability_quality: str
    cashflow_quality: str
    growth_and_industry: str
    major_risks: str
    tracking_checklist: list[str]
    source_notes: list[SourceNote]
    source_summary: dict
    confidence_score: int
    limitations: list[str]
    key_metrics: dict = field(default_factory=dict)
    compare_metrics: list[dict] = field(default_factory=list)

    def to_public_dict(self) -> dict:
        return asdict(self)
