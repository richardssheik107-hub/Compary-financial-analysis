from __future__ import annotations

import re
from typing import Any

from src.agent import _extract_company_mentions, run_financial_agent
from src.ai_client import analyze_general_question
from src.data_service import build_company_snapshot
from src.report_loader import load_research_documents, retrieve_relevant_passages, unsupported_source_note
from src.research_models import CompanyResearchContext, ResearchDocument, ResearchResult, SourceNote
from src.research_skill import refine_research_result

BUSINESS_KEYS = ["主营", "业务", "产品", "客户", "市场", "行业", "模式"]
MANAGEMENT_KEYS = ["管理层", "经营", "战略", "展望", "计划", "目标", "产能"]
RESEARCH_KEYS = ["研报", "券商", "观点", "评级", "预测", "空间", "行业"]
RISK_KEYS = ["风险", "压力", "不确定", "下滑", "竞争", "减值", "政策"]


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).replace(",", "").replace("亿元", "").replace("%", "").strip()
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[。！？])", (text or "").replace("\n", "。"))
    return [p.strip() for p in parts if len(p.strip()) >= 12]


def _pick_sentences(documents: list[ResearchDocument], keywords: list[str], limit: int) -> list[str]:
    picked: list[str] = []
    for doc in documents:
        for sentence in _split_sentences(doc.content):
            if any(key in sentence for key in keywords):
                picked.append(f"{sentence}（来源：{doc.title}）")
            if len(picked) >= limit:
                return picked
    return picked


def summarize_company_sources(documents: list[ResearchDocument], query: str) -> dict[str, list[str]]:
    rag_hits = retrieve_relevant_passages(documents, query, top_k=8)
    rag_lines = [f"{text}（来源：{doc.title}）" for doc, text in rag_hits[:4]]
    return {
        "business_segments": rag_lines[:2] + _pick_sentences(documents, BUSINESS_KEYS, 2),
        "management_discussion": _pick_sentences(documents, MANAGEMENT_KEYS, 3),
        "research_views": rag_lines[2:4] + _pick_sentences(documents, RESEARCH_KEYS, 2),
        "risks": _pick_sentences(documents, RISK_KEYS, 4),
    }


def _source_notes_from_documents(documents: list[ResearchDocument]) -> list[SourceNote]:
    return [
        SourceNote(source_type=doc.source_type, title=doc.title, detail="本地资料命中", file_path=doc.file_path)
        for doc in documents
    ]


def build_company_research_context(query_or_code: str, query: str = "") -> CompanyResearchContext:
    snapshot = build_company_snapshot(query_or_code)
    company_name = str(snapshot.get("company_name") or query_or_code)
    stock_code = str(snapshot.get("stock_code") or "")
    documents, source_summary = load_research_documents(company_name, stock_code)
    summaries = summarize_company_sources(documents, query or query_or_code)

    source_notes = [
        SourceNote(source_type="财务数据", title="AKShare/本地快照", detail=str(snapshot.get("data_source", "unknown"))),
        *_source_notes_from_documents(documents),
        unsupported_source_note(),
    ]
    company_profile = " ".join(summaries["business_segments"][:2]).strip() or f"{company_name} 当前优先基于财务摘要进行研究。"

    return CompanyResearchContext(
        company_name=company_name,
        stock_code=stock_code,
        company_profile=company_profile,
        financial_metrics=snapshot.get("financial_metrics", {}),
        business_segments=summaries["business_segments"],
        management_discussion=summaries["management_discussion"],
        research_views=summaries["research_views"],
        risks=summaries["risks"],
        source_notes=source_notes,
        data_quality=snapshot.get("data_quality", {}),
        source_summary=source_summary,
    )


def _metric(metrics: dict[str, Any], key: str, default: str = "暂未取得") -> str:
    value = metrics.get(key)
    return str(value) if value not in (None, "") else default


def _confidence(context: CompanyResearchContext) -> int:
    score = 45
    metrics = context.financial_metrics
    score += min(25, len([v for v in metrics.values() if v]) * 4)
    if context.business_segments:
        score += 10
    if context.management_discussion:
        score += 8
    if context.research_views:
        score += 8
    if context.risks:
        score += 4
    return max(0, min(95, score))


def _limitations(context: CompanyResearchContext) -> list[str]:
    items: list[str] = []
    if not context.business_segments:
        items.append("未命中业务文本，业务判断偏推断。")
    if not context.research_views:
        items.append("未命中研报观点，行业视角不足。")
    if not context.risks:
        items.append("风险段落来源不足，需补充公告或研报。")
    return items or ["基于当前资料生成，仍需结合最新公告复核。"]


def _join_or_infer(items: list[str], fallback: str) -> str:
    return " ".join(items[:3]) if items else f"{fallback}（模型推断）"


def _build_evidence_map(context: CompanyResearchContext) -> dict:
    return {
        "一句话结论": ["财务数据", "模型推理"],
        "业务概览": ["年报文本", "公司资料", "模型推理"],
        "经营表现": ["财务数据"],
        "盈利质量": ["财务数据", "模型推理"],
        "现金流质量": ["财务数据", "模型推理"],
        "成长与行业": ["研报观点", "行业资料", "模型推理"],
        "主要风险": ["年报文本", "研报观点", "模型推理"],
    }


def research_company(query: str) -> ResearchResult:
    context = build_company_research_context(query, query)
    metrics = context.financial_metrics
    result = ResearchResult(
        report_type="single_company_research",
        title=f"{context.company_name} 经营研究报告",
        one_line_conclusion=(
            f"{context.company_name} 当前重点看收入、利润和现金流是否同步改善；"
            f"收入{_metric(metrics, 'revenue')}，净利润{_metric(metrics, 'net_profit')}，经营现金流{_metric(metrics, 'operating_cash_flow')}。"
        ),
        business_overview=_join_or_infer(context.business_segments, f"{context.company_name} 业务信息有待补充。"),
        operating_performance=(
            f"收入{_metric(metrics, 'revenue')}（同比{_metric(metrics, 'revenue_yoy')}），"
            f"净利润{_metric(metrics, 'net_profit')}（同比{_metric(metrics, 'net_profit_yoy')}），"
            f"经营现金流{_metric(metrics, 'operating_cash_flow')}。"
        ),
        profitability_quality="盈利质量需关注利润增长是否来自主营，后续建议结合毛利率、费用率和ROE验证。",
        cashflow_quality=(
            f"经营现金流{_metric(metrics, 'operating_cash_flow')}，需与净利润{_metric(metrics, 'net_profit')}长期对照，"
            "若现金流持续弱于利润，需警惕利润含金量。"
        ),
        growth_and_industry=_join_or_infer(context.management_discussion + context.research_views, "成长性需结合行业空间和竞争格局判断。"),
        major_risks=_join_or_infer(context.risks, "主要风险包括需求波动、竞争加剧和政策变化。"),
        tracking_checklist=[
            "下一期收入、净利润、经营现金流是否同向改善",
            "毛利率、费用率、ROE是否稳定",
            "管理层展望是否兑现",
        ],
        source_notes=context.source_notes,
        source_summary=context.source_summary,
        confidence_score=_confidence(context),
        limitations=_limitations(context),
        evidence_by_section=_build_evidence_map(context),
        key_metrics={
            "company": context.company_name,
            "revenue": _to_float(metrics.get("revenue")),
            "net_profit": _to_float(metrics.get("net_profit")),
            "operating_cash_flow": _to_float(metrics.get("operating_cash_flow")),
        },
        compare_metrics=[],
    )
    return refine_research_result(result, query)


def compare_companies_deep(query: str, agent_result: Any | None = None) -> ResearchResult | None:
    agent_result = agent_result or run_financial_agent(query)
    if not agent_result.comparison:
        return None
    company_a = agent_result.comparison.get("company_a", {})
    company_b = agent_result.comparison.get("company_b", {})
    context_a = build_company_research_context(str(company_a.get("code") or company_a.get("name") or ""), query)
    context_b = build_company_research_context(str(company_b.get("code") or company_b.get("name") or ""), query)
    a_metrics, b_metrics = context_a.financial_metrics, context_b.financial_metrics
    winner = str(agent_result.comparison.get("winner") or context_a.company_name)
    reason = str(agent_result.comparison.get("winner_reason") or "综合财务表现更好")

    result = ResearchResult(
        report_type="compare_companies_deep",
        title=f"{context_a.company_name} vs {context_b.company_name} 深度对比",
        one_line_conclusion=f"当前更值得优先研究的是{winner}，主要原因是：{reason}。",
        business_overview=f"{context_a.company_name}：{context_a.company_profile} {context_b.company_name}：{context_b.company_profile}",
        operating_performance=(
            f"{context_a.company_name}收入{_metric(a_metrics, 'revenue')}、净利润{_metric(a_metrics, 'net_profit')}；"
            f"{context_b.company_name}收入{_metric(b_metrics, 'revenue')}、净利润{_metric(b_metrics, 'net_profit')}。"
        ),
        profitability_quality=(
            f"{context_a.company_name}净利润同比{_metric(a_metrics, 'net_profit_yoy')}；"
            f"{context_b.company_name}净利润同比{_metric(b_metrics, 'net_profit_yoy')}。"
        ),
        cashflow_quality=(
            f"{context_a.company_name}经营现金流{_metric(a_metrics, 'operating_cash_flow')}；"
            f"{context_b.company_name}经营现金流{_metric(b_metrics, 'operating_cash_flow')}。"
        ),
        growth_and_industry="成长性需结合行业空间、竞争格局和管理层执行力，而不仅是单期增速。",
        major_risks=(
            f"{context_a.company_name}风险：{_join_or_infer(context_a.risks, '资料不足')} "
            f"{context_b.company_name}风险：{_join_or_infer(context_b.risks, '资料不足')}"
        ),
        tracking_checklist=["报告期口径是否一致", "收入利润现金流是否同向改善", "风险是否出现新变化"],
        source_notes=[*context_a.source_notes, *context_b.source_notes],
        source_summary={
            "reports": int(context_a.source_summary.get("reports", 0)) + int(context_b.source_summary.get("reports", 0)),
            "company_info": int(context_a.source_summary.get("company_info", 0)) + int(context_b.source_summary.get("company_info", 0)),
            "industry_info": int(context_a.source_summary.get("industry_info", 0)) + int(context_b.source_summary.get("industry_info", 0)),
            "total": int(context_a.source_summary.get("total", 0)) + int(context_b.source_summary.get("total", 0)),
        },
        confidence_score=min(_confidence(context_a), _confidence(context_b)),
        limitations=list(dict.fromkeys([*_limitations(context_a), *_limitations(context_b)])),
        evidence_by_section=_build_evidence_map(context_a),
        key_metrics={},
        compare_metrics=[
            {"metric": "revenue", "label": "营业收入(亿元)", "a": _to_float(a_metrics.get("revenue")), "b": _to_float(b_metrics.get("revenue")), "company_a": context_a.company_name, "company_b": context_b.company_name},
            {"metric": "net_profit", "label": "净利润(亿元)", "a": _to_float(a_metrics.get("net_profit")), "b": _to_float(b_metrics.get("net_profit")), "company_a": context_a.company_name, "company_b": context_b.company_name},
            {"metric": "operating_cash_flow", "label": "经营现金流(亿元)", "a": _to_float(a_metrics.get("operating_cash_flow")), "b": _to_float(b_metrics.get("operating_cash_flow")), "company_a": context_a.company_name, "company_b": context_b.company_name},
        ],
    )
    return refine_research_result(result, query)


def general_business_qa(query: str) -> ResearchResult:
    analysis = analyze_general_question(query)
    answer = " ".join([analysis.plain_cashflow_summary, analysis.future_outlook, analysis.risk_notes]).strip()
    if not answer:
        answer = "请补充具体公司，可输出更完整经营研究。"
    result = ResearchResult(
        report_type="general_business_qa",
        title="通用经营问题回答",
        one_line_conclusion=answer,
        business_overview="通用问题不绑定具体公司，不输出公司画像。",
        operating_performance="通用问题不绑定具体公司，不输出具体经营数据。",
        profitability_quality="看盈利质量重点关注利润来源和可持续性。",
        cashflow_quality="看现金流质量重点关注经营现金流与净利润的匹配度。",
        growth_and_industry="看成长性需同时看行业空间与竞争格局。",
        major_risks="本回答不构成投资建议，也不预测股价。",
        tracking_checklist=["补充具体公司", "对照收入利润现金流", "复核风险点"],
        source_notes=[SourceNote(source_type="模型推理", title="通用框架", detail="未绑定具体公司")],
        source_summary={"reports": 0, "company_info": 0, "industry_info": 0, "total": 0},
        confidence_score=60,
        limitations=["未绑定具体公司，无法引用公司级证据。"],
        evidence_by_section={"通用回答": ["模型推理"]},
        key_metrics={},
        compare_metrics=[],
    )
    return refine_research_result(result, query)


def run_company_research_agent(
    query: str,
    *,
    context_company_name: str = "",
    context_stock_code: str = "",
) -> ResearchResult:
    base = run_financial_agent(query, context_company_name=context_company_name, context_stock_code=context_stock_code)
    if base.snapshot.get("stock_code") == "N/A":
        mentions = _extract_company_mentions(base.resolved_query or query)
        if mentions:
            return research_company(mentions[0])
        return general_business_qa(base.resolved_query or query)
    compare_result = compare_companies_deep(base.resolved_query or query, base)
    if compare_result is not None:
        return compare_result
    return research_company(base.resolved_query or query)
