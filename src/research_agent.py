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


def summarize_company_sources(company: str, documents: list[ResearchDocument], query: str) -> dict[str, list[str]]:
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
    summaries = summarize_company_sources(company_name, documents, query or query_or_code)

    source_notes = [
        SourceNote(source_type="财务数据", title="AKShare/本地快照", detail=str(snapshot.get("data_source", "unknown"))),
        *_source_notes_from_documents(documents),
        unsupported_source_note(),
    ]

    company_profile = " ".join(summaries["business_segments"][:2]).strip()
    if not company_profile:
        company_profile = f"{company_name} 当前主要依据公开财务摘要进行初步研究，本地年报/研报资料暂未命中。"

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
        items.append("未命中本地年报/季报业务描述，业务判断主要来自财务摘要与模型推断。")
    if not context.research_views:
        items.append("未命中本地研报观点，暂不纳入券商预测或行业观点。")
    if not context.risks:
        items.append("风险项缺少本地文本支撑，需继续补充公告或研报。")
    return items or ["本报告基于当前已加载资料生成，仍需结合最新公告复核。"]


def _join_or_infer(items: list[str], fallback: str) -> str:
    if items:
        return " ".join(items[:3])
    return f"{fallback}（模型推断）"


def research_company(query: str) -> ResearchResult:
    context = build_company_research_context(query, query)
    metrics = context.financial_metrics
    revenue = _metric(metrics, "revenue")
    profit = _metric(metrics, "net_profit")
    cashflow = _metric(metrics, "operating_cash_flow")
    revenue_yoy = _metric(metrics, "revenue_yoy")
    profit_yoy = _metric(metrics, "net_profit_yoy")

    result = ResearchResult(
        report_type="single_company_research",
        title=f"{context.company_name} 经营研究报告",
        one_line_conclusion=f"{context.company_name} 当前研究重点是收入增长、利润质量与经营现金流是否同向改善；已取得收入 {revenue}、净利润 {profit}、经营现金流 {cashflow}。",
        business_overview=_join_or_infer(context.business_segments, f"{context.company_name} 的业务画像需要继续补充年报主营业务信息。"),
        operating_performance=f"近年经营表现先看三项：收入 {revenue}（同比 {revenue_yoy}）、净利润 {profit}（同比 {profit_yoy}）、经营现金流 {cashflow}。",
        profitability_quality="盈利质量要看利润增长是否来自主营业务，是否依赖一次性收益；后续可补充毛利率、费用率和 ROE 进一步验证。",
        cashflow_quality=f"现金流质量方面，经营现金流为 {cashflow}。应与净利润 {profit} 对照：长期弱于利润通常意味着利润含金量不足。",
        growth_and_industry=_join_or_infer(context.management_discussion + context.research_views, "成长性需结合行业空间、竞争格局和管理层执行判断。"),
        major_risks=_join_or_infer(context.risks, "主要风险包括需求波动、行业竞争、盈利能力下滑和政策周期变化。"),
        tracking_checklist=[
            "下一期收入和利润是否继续同向增长",
            "经营现金流是否能覆盖净利润",
            "毛利率、费用率和 ROE 是否稳定",
            "管理层展望是否与经营数据一致",
            "是否出现新的政策或竞争风险",
        ],
        source_notes=context.source_notes,
        source_summary=context.source_summary,
        key_metrics={
            "company": context.company_name,
            "revenue": _to_float(metrics.get("revenue")),
            "net_profit": _to_float(metrics.get("net_profit")),
            "operating_cash_flow": _to_float(metrics.get("operating_cash_flow")),
            "revenue_yoy": _to_float(metrics.get("revenue_yoy")),
            "net_profit_yoy": _to_float(metrics.get("net_profit_yoy")),
        },
        compare_metrics=[],
        confidence_score=_confidence(context),
        limitations=_limitations(context),
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

    a_metrics = context_a.financial_metrics
    b_metrics = context_b.financial_metrics
    winner = str(agent_result.comparison.get("winner") or context_a.company_name)
    reason = str(agent_result.comparison.get("winner_reason") or "综合财务表现更好")

    result = ResearchResult(
        report_type="compare_companies_deep",
        title=f"{context_a.company_name} vs {context_b.company_name} 深度对比",
        one_line_conclusion=f"当前更值得优先研究的是 {winner}，主要原因是{reason}；但结论仍需结合后续财报和行业资料复核。",
        business_overview=f"{context_a.company_name}：{context_a.company_profile} {context_b.company_name}：{context_b.company_profile}",
        operating_performance=f"{context_a.company_name} 收入 {_metric(a_metrics, 'revenue')}、利润 {_metric(a_metrics, 'net_profit')}；{context_b.company_name} 收入 {_metric(b_metrics, 'revenue')}、利润 {_metric(b_metrics, 'net_profit')}。",
        profitability_quality=f"{context_a.company_name} 净利润同比 {_metric(a_metrics, 'net_profit_yoy')}；{context_b.company_name} 净利润同比 {_metric(b_metrics, 'net_profit_yoy')}。",
        cashflow_quality=f"{context_a.company_name} 经营现金流 {_metric(a_metrics, 'operating_cash_flow')}；{context_b.company_name} 经营现金流 {_metric(b_metrics, 'operating_cash_flow')}。",
        growth_and_industry="成长性不能只看单期增速，还要看业务空间、竞争格局和管理层执行。",
        major_risks=f"{context_a.company_name} 风险：{_join_or_infer(context_a.risks, '需继续补充风险资料')} {context_b.company_name} 风险：{_join_or_infer(context_b.risks, '需继续补充风险资料')}",
        tracking_checklist=[
            "两家公司是否处在同一报告期口径",
            "收入、利润、现金流是否同步改善",
            "毛利率、费用率和 ROE 是否出现背离",
            "研报观点是否支持财务数据结论",
            "是否出现新的政策、周期或竞争风险",
        ],
        source_notes=[*context_a.source_notes, *context_b.source_notes],
        source_summary={
            "reports": int(context_a.source_summary.get("reports", 0)) + int(context_b.source_summary.get("reports", 0)),
            "company_info": int(context_a.source_summary.get("company_info", 0)) + int(context_b.source_summary.get("company_info", 0)),
            "industry_info": int(context_a.source_summary.get("industry_info", 0)) + int(context_b.source_summary.get("industry_info", 0)),
            "total": int(context_a.source_summary.get("total", 0)) + int(context_b.source_summary.get("total", 0)),
        },
        key_metrics={},
        compare_metrics=[
            {"metric": "revenue", "label": "营业收入(亿元)", "a": _to_float(a_metrics.get("revenue")), "b": _to_float(b_metrics.get("revenue")), "company_a": context_a.company_name, "company_b": context_b.company_name},
            {"metric": "net_profit", "label": "净利润(亿元)", "a": _to_float(a_metrics.get("net_profit")), "b": _to_float(b_metrics.get("net_profit")), "company_a": context_a.company_name, "company_b": context_b.company_name},
            {"metric": "operating_cash_flow", "label": "经营现金流(亿元)", "a": _to_float(a_metrics.get("operating_cash_flow")), "b": _to_float(b_metrics.get("operating_cash_flow")), "company_a": context_a.company_name, "company_b": context_b.company_name},
        ],
        confidence_score=min(_confidence(context_a), _confidence(context_b)),
        limitations=list(dict.fromkeys([*_limitations(context_a), *_limitations(context_b)])),
    )
    return refine_research_result(result, query)


def general_business_qa(query: str) -> ResearchResult:
    analysis = analyze_general_question(query)
    answer = " ".join(
        item for item in [analysis.plain_cashflow_summary, analysis.future_outlook, analysis.risk_notes] if item
    )
    if not answer:
        answer = "这个问题需要结合收入、利润、现金流、资产负债和行业背景一起判断；如补充具体公司可进一步做公司级研究。"

    result = ResearchResult(
        report_type="general_business_qa",
        title="通用经营问题回答",
        one_line_conclusion=answer,
        business_overview="通用问题不绑定具体公司，因此不展示业务画像。",
        operating_performance="通用问题不绑定具体公司，因此不展示具体经营数据。",
        profitability_quality="判断盈利质量时，要看利润是否来自主营业务、是否可持续，以及是否被一次性收益放大。",
        cashflow_quality="判断现金流质量时，要把经营现金流和净利润对照看，长期现金流弱于利润通常说明利润含金量不足。",
        growth_and_industry="判断成长性时，要同时看行业空间、竞争格局、公司份额变化和管理层执行，而不能只看单期增速。",
        major_risks="通用回答不构成投资建议，也不预测股价；实际研究时需要补充具体公司的公告、年报和行业资料。",
        tracking_checklist=[
            "先确认问题对应的行业和公司",
            "再对照收入、利润、现金流是否同向改善",
            "最后检查风险因素和后续验证指标",
        ],
        source_notes=[SourceNote(source_type="模型推理", title="通用经营问题", detail="未绑定具体公司，回答来自通用财务分析框架。")],
        source_summary={"reports": 0, "company_info": 0, "industry_info": 0, "total": 0},
        key_metrics={},
        compare_metrics=[],
        confidence_score=60,
        limitations=["未绑定具体公司，无法引用公司财务数据、年报或研报。"],
    )
    return refine_research_result(result, query)


def run_company_research_agent(query: str) -> ResearchResult:
    agent_result = run_financial_agent(query)
    if agent_result.snapshot.get("stock_code") == "N/A":
        mentions = _extract_company_mentions(query)
        if mentions:
            return research_company(mentions[0])
        return general_business_qa(query)
    compare_result = compare_companies_deep(query, agent_result)
    if compare_result is not None:
        return compare_result
    return research_company(query)
