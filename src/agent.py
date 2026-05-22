from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata
from typing import Any, Callable

from src.ai_client import analyze_company, analyze_general_question
from src.company_aliases import load_aliases
from src.data_service import build_company_snapshot
from src.models import AgentResult, AgentStep, EvaluationResult, ToolCallResult


@dataclass
class ToolRegistry:
    tools: dict[str, Callable[..., Any]]

    def call(self, tool_name: str, *args: Any, **kwargs: Any) -> Any:
        if tool_name not in self.tools:
            raise ValueError(f"Tool not found: {tool_name}")
        return self.tools[tool_name](*args, **kwargs)


def _build_registry() -> ToolRegistry:
    return ToolRegistry(
        tools={
            "build_company_snapshot": build_company_snapshot,
            "analyze_company": analyze_company,
            "analyze_general_question": analyze_general_question,
        }
    )


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", (text or "").strip().lower())
    return re.sub(r"\s+", "", normalized)


def _extract_company_mentions(query: str) -> list[str]:
    normalized = _normalize_text(query)
    mentions: list[str] = []
    alias_to_canonical = load_aliases(force_reload=True)

    for code in re.findall(r"\b\d{6}\b", normalized):
        if code not in mentions:
            mentions.append(code)

    for alias, canonical in sorted(alias_to_canonical.items(), key=lambda x: len(x[0]), reverse=True):
        if alias in normalized and canonical not in mentions:
            mentions.append(canonical)
    return mentions


def _has_compare_keyword(normalized: str) -> bool:
    compare_keywords = ["对比", "比较", "谁更好", "哪个好", "哪个更好", "更稳", "更强", "vs", "versus"]
    return any(k in normalized for k in compare_keywords)


def _detect_intent(query: str) -> str:
    normalized = _normalize_text(query)
    if not normalized:
        return "未提供问题"

    mentions = _extract_company_mentions(normalized)
    if (len(mentions) >= 2 and _has_compare_keyword(normalized)) or len(re.findall(r"\b\d{6}\b", normalized)) >= 2:
        return "财报对比"

    finance_keywords = ["现金流", "利润", "营收", "收入", "财报", "年报", "季报", "估值", "增长"]
    if mentions or any(k in normalized for k in finance_keywords):
        return "财报解读"
    return "通用财报问答"


def _has_explicit_target(query: str) -> bool:
    return len(_extract_company_mentions(query)) >= 1


def _apply_context_to_query(query: str, context_company_name: str, context_stock_code: str) -> tuple[str, bool]:
    normalized = (query or "").strip()
    if not normalized:
        return normalized, False
    if not (context_company_name or context_stock_code):
        return normalized, False
    if _has_explicit_target(normalized):
        return normalized, False

    followup_signals = ["它", "这家公司", "这家", "上一家", "刚才这家", "继续", "再看", "进一步", "那它"]
    generic_signals = ["怎么看", "如何", "风险", "利润", "现金流", "营收", "增速", "估值", "还能"]
    if any(s in normalized for s in followup_signals) or len(normalized) <= 28 or any(s in normalized for s in generic_signals):
        target = context_company_name or context_stock_code
        return f"{target}，{normalized}", True
    return normalized, False


def _extract_compare_targets(query: str) -> list[str]:
    mentions = _extract_company_mentions(query)
    unique: list[str] = []
    for item in mentions:
        if item not in unique:
            unique.append(item)
    return unique[:4]


def _looks_like_compare_query(query: str) -> bool:
    normalized = _normalize_text(query)
    mentions = _extract_company_mentions(normalized)
    return (len(mentions) >= 2 and _has_compare_keyword(normalized)) or len(re.findall(r"\b\d{6}\b", normalized)) >= 2


def _to_float_metric(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).replace("亿元", "").replace("%", "").replace(",", "").strip()
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _evaluate_output(snapshot: dict[str, Any], analysis: Any) -> EvaluationResult | None:
    if analysis is None:
        return None
    text = f"{analysis.plain_cashflow_summary} {analysis.future_outlook} {analysis.risk_notes}"
    forbidden_words = ["买入", "卖出", "重仓", "满仓", "清仓", "梭哈"]
    has_forbidden = any(word in text for word in forbidden_words)
    has_risk = "不构成投资建议" in analysis.risk_notes
    has_data_source = bool(snapshot.get("data_source"))
    explains_core_metrics = all(word in analysis.plain_cashflow_summary for word in ["收入", "利润", "现金流"])

    notes: list[str] = []
    if not has_risk:
        notes.append("缺少标准风险提示。")
    if not has_data_source:
        notes.append("缺少数据来源标记。")
    if has_forbidden:
        notes.append("出现直接交易指令词。")
    if not explains_core_metrics:
        notes.append("白话解读未完整覆盖收入、利润、现金流。")

    quality_score = 100
    if not has_risk:
        quality_score -= 30
    if not has_data_source:
        quality_score -= 15
    if has_forbidden:
        quality_score -= 40
    if not explains_core_metrics:
        quality_score -= 15
    quality_score = max(0, min(100, quality_score))

    return EvaluationResult(
        has_risk_note=has_risk,
        has_data_source=has_data_source,
        has_forbidden_advice=has_forbidden,
        explains_core_metrics=explains_core_metrics,
        quality_score=quality_score,
        notes=notes,
    )


def _build_compare_summary(snapshot_a: dict[str, Any], snapshot_b: dict[str, Any], analysis_a: Any, analysis_b: Any) -> dict[str, Any]:
    metrics_a = snapshot_a.get("financial_metrics", {})
    metrics_b = snapshot_b.get("financial_metrics", {})
    score_a = round((analysis_a.scores.profitability + analysis_a.scores.cash_saving + analysis_a.scores.future_potential) / 3, 2)
    score_b = round((analysis_b.scores.profitability + analysis_b.scores.cash_saving + analysis_b.scores.future_potential) / 3, 2)

    winner = snapshot_a.get("company_name", "公司A")
    reason = "综合评分更高"
    if score_b > score_a:
        winner = snapshot_b.get("company_name", "公司B")
    a_growth = (_to_float_metric(metrics_a.get("revenue_yoy")) or 0) + (_to_float_metric(metrics_a.get("net_profit_yoy")) or 0)
    b_growth = (_to_float_metric(metrics_b.get("revenue_yoy")) or 0) + (_to_float_metric(metrics_b.get("net_profit_yoy")) or 0)
    if b_growth > a_growth:
        winner = snapshot_b.get("company_name", "公司B")
        reason = "营收和利润增速合计更强"
    elif a_growth > b_growth:
        winner = snapshot_a.get("company_name", "公司A")
        reason = "营收和利润增速合计更强"

    return {
        "is_compare": True,
        "company_a": {"name": snapshot_a.get("company_name", ""), "code": snapshot_a.get("stock_code", ""), "score": score_a},
        "company_b": {"name": snapshot_b.get("company_name", ""), "code": snapshot_b.get("stock_code", ""), "score": score_b},
        "winner": winner,
        "winner_reason": reason,
        "industry_context": "当前结论主要基于财报核心指标与 AI 解读，不等同于完整行业景气度或估值判断。",
        "confidence_score": 85,
        "limitations": [],
        "followups": [
            f"继续对比 {snapshot_a.get('company_name', '公司A')} 和 {snapshot_b.get('company_name', '公司B')} 的毛利率与净利率变化。",
            "补充看最近两期财报，确认营收增长是否伴随现金流同步改善。",
            "针对领先公司继续追问：增长持续性的最大风险来自哪里？",
        ],
        "rows": [
            {"metric": "营收同比", "a": str(metrics_a.get("revenue_yoy", "暂无")), "b": str(metrics_b.get("revenue_yoy", "暂无"))},
            {"metric": "净利润同比", "a": str(metrics_a.get("net_profit_yoy", "暂无")), "b": str(metrics_b.get("net_profit_yoy", "暂无"))},
            {"metric": "经营现金流", "a": str(metrics_a.get("operating_cash_flow", "暂无")), "b": str(metrics_b.get("operating_cash_flow", "暂无"))},
            {"metric": "AI 情绪", "a": analysis_a.sentiment_label, "b": analysis_b.sentiment_label},
        ],
    }


def _build_general_followups(intent: str, snapshot: dict[str, Any], analysis: Any) -> list[str]:
    company = snapshot.get("company_name", "")
    if intent == "通用财报问答":
        return [
            "请按一个具体行业举例，说明收入、利润、现金流应该怎么看。",
            "帮我给出两个可对比的 A 股公司，并按同一口径做对比。",
            "如果我是新手，先看哪三个财报指标最不容易踩坑？",
        ]
    if company and company != "通用问题模式":
        return [
            f"继续分析 {company} 最近两期财报里利润和现金流是否同步改善。",
            f"请解释 {company} 当前最大的经营风险来自哪里，以及如何跟踪。",
            f"把 {company} 和同行龙头做一版核心指标对比。",
        ]
    if analysis is not None:
        return ["请把刚才结论改写成三条可执行的观察清单。", "再给我一个更保守视角下的风险复盘。"]
    return []


def _fallback_to_single_company(
    *,
    query: str,
    effective_query: str,
    context_used: bool,
    context_company_name: str,
    context_stock_code: str,
    steps: list[AgentStep],
    tool_calls: list[ToolCallResult],
    warnings: list[str],
    snapshot: dict[str, Any],
    registry: ToolRegistry,
) -> AgentResult:
    analysis = registry.call("analyze_company", snapshot, effective_query)
    tool_calls.append(ToolCallResult(tool_name="analyze_company", success=True, summary=analysis.ai_status))
    steps.append(AgentStep(step_name="单公司回退解读", status="success", summary=f"已回退为单公司分析：{snapshot.get('company_name')}", tool_name="analyze_company"))
    warnings.append("检测到对比意图，但仅识别到一个公司，已自动回退为单公司解读。")
    if snapshot.get("data_warning"):
        warnings.append(snapshot["data_warning"])
    if snapshot.get("price_warning"):
        warnings.append(snapshot["price_warning"])
    evaluation = _evaluate_output(snapshot, analysis)
    return AgentResult(
        query=query,
        resolved_query=effective_query,
        intent="财报解读",
        steps=steps,
        tool_calls=tool_calls,
        analysis=analysis,
        snapshot=snapshot,
        warnings=warnings,
        data_quality=snapshot.get("data_quality", {}),
        evaluation=evaluation,
        comparison=None,
        suggested_questions=_build_general_followups("财报解读", snapshot, analysis),
        context_used=context_used,
        context_company_name=context_company_name,
        context_stock_code=context_stock_code,
    )


def run_financial_agent(
    query: str,
    *,
    resolved_query: str | None = None,
    context_company_name: str = "",
    context_stock_code: str = "",
    context_used: bool = False,
) -> AgentResult:
    registry = _build_registry()
    steps: list[AgentStep] = []
    tool_calls: list[ToolCallResult] = []
    warnings: list[str] = []

    if resolved_query:
        effective_query = resolved_query
    else:
        effective_query, auto_context_used = _apply_context_to_query(query, context_company_name, context_stock_code)
        context_used = context_used or auto_context_used
    intent = _detect_intent(effective_query)

    if not (query or "").strip():
        steps.append(AgentStep(step_name="输入校验", status="failed", summary="未提供有效问题", tool_name="validate_query", error="empty_query"))
        return AgentResult(
            query=query,
            resolved_query=effective_query,
            intent=intent,
            steps=steps,
            tool_calls=tool_calls,
            analysis=None,
            snapshot={"found": False, "data_warning": "请输入公司简称、股票代码，或一句自然语言问题。"},
            warnings=["输入为空，未触发数据分析。"],
            data_quality={"live_metric_count": 0, "fallback_enabled": True, "report_period": "not_started"},
            evaluation=None,
            comparison=None,
            suggested_questions=["先告诉我你想看哪个公司，或说“帮我选两个公司做对比”。"],
            context_used=context_used,
            context_company_name=context_company_name,
            context_stock_code=context_stock_code,
        )

    steps.append(AgentStep(step_name="意图识别", status="success", summary=f"识别为：{intent}", tool_name="detect_intent"))

    if intent == "财报对比" or _looks_like_compare_query(effective_query):
        targets = _extract_compare_targets(effective_query)
        snapshots: list[dict[str, Any]] = []
        analyses: list[Any] = []
        for target in targets:
            snapshot = registry.call("build_company_snapshot", target)
            tool_calls.append(
                ToolCallResult(
                    tool_name="build_company_snapshot",
                    success=bool(snapshot.get("found")),
                    summary=f"target={target} found={snapshot.get('found')} source={snapshot.get('data_source', 'unknown')}",
                    error="" if snapshot.get("found") else snapshot.get("data_warning", "not_found"),
                )
            )
            if snapshot.get("found"):
                snapshots.append(snapshot)
                steps.append(AgentStep(step_name="对比目标识别", status="success", summary=f"已识别：{snapshot.get('company_name')} ({snapshot.get('stock_code')})", tool_name="build_company_snapshot"))
            if len(snapshots) == 2:
                break

        if len(snapshots) == 1:
            return _fallback_to_single_company(
                query=query,
                effective_query=effective_query,
                context_used=context_used,
                context_company_name=context_company_name,
                context_stock_code=context_stock_code,
                steps=steps,
                tool_calls=tool_calls,
                warnings=warnings,
                snapshot=snapshots[0],
                registry=registry,
            )

        if len(snapshots) < 2:
            steps.append(AgentStep(step_name="对比分析", status="failed", summary="未识别到两个有效公司，无法生成对比结果", tool_name="build_company_snapshot", error="compare_targets_not_enough"))
            warnings.append("检测到对比意图，但未识别到两个公司。请明确提供两个公司名称或代码。")
            return AgentResult(
                query=query,
                resolved_query=effective_query,
                intent="财报对比",
                steps=steps,
                tool_calls=tool_calls,
                analysis=None,
                snapshot={"found": False, "data_warning": "未识别到两个可对比公司。"},
                warnings=warnings,
                data_quality={},
                evaluation=None,
                comparison=None,
                suggested_questions=["试试：宁德时代和比亚迪谁更好？", "试试：平安银行和招商银行哪个更稳？"],
                context_used=context_used,
                context_company_name=context_company_name,
                context_stock_code=context_stock_code,
            )

        for snapshot in snapshots:
            analysis = registry.call("analyze_company", snapshot, effective_query)
            analyses.append(analysis)
            tool_calls.append(ToolCallResult(tool_name="analyze_company", success=True, summary=f"{snapshot.get('company_name')} -> {analysis.ai_status}"))
        steps.append(AgentStep(step_name="对比结论生成", status="success", summary=f"已完成 {snapshots[0].get('company_name')} 与 {snapshots[1].get('company_name')} 对比", tool_name="compare_synthesizer"))
        comparison = _build_compare_summary(snapshots[0], snapshots[1], analyses[0], analyses[1])
        evaluation = _evaluate_output(snapshots[0], analyses[0])
        return AgentResult(
            query=query,
            resolved_query=effective_query,
            intent="财报对比",
            steps=steps,
            tool_calls=tool_calls,
            analysis=analyses[0],
            snapshot=snapshots[0],
            warnings=warnings,
            data_quality=snapshots[0].get("data_quality", {}),
            evaluation=evaluation,
            comparison=comparison,
            suggested_questions=comparison.get("followups", []),
            context_used=context_used,
            context_company_name=context_company_name,
            context_stock_code=context_stock_code,
        )

    snapshot = registry.call("build_company_snapshot", effective_query)
    tool_calls.append(ToolCallResult(tool_name="build_company_snapshot", success=bool(snapshot.get("found")), summary=f"found={snapshot.get('found')} source={snapshot.get('data_source', 'unknown')}", error="" if snapshot.get("found") else snapshot.get("data_warning", "not_found")))
    if snapshot.get("found"):
        steps.append(AgentStep(step_name="公司识别与数据抓取", status="success", summary=f"已识别目标：{snapshot.get('company_name')} ({snapshot.get('stock_code')})", tool_name="build_company_snapshot"))
        analysis = registry.call("analyze_company", snapshot, effective_query)
        tool_calls.append(ToolCallResult(tool_name="analyze_company", success=True, summary=analysis.ai_status))
        steps.append(AgentStep(step_name="财报解读生成", status="success", summary=f"解读完成：{analysis.ai_status}", tool_name="analyze_company"))
        if snapshot.get("data_warning"):
            warnings.append(snapshot["data_warning"])
        if snapshot.get("price_warning"):
            warnings.append(snapshot["price_warning"])
        evaluation = _evaluate_output(snapshot, analysis)
        return AgentResult(
            query=query,
            resolved_query=effective_query,
            intent="财报解读",
            steps=steps,
            tool_calls=tool_calls,
            analysis=analysis,
            snapshot=snapshot,
            warnings=warnings,
            data_quality=snapshot.get("data_quality", {}),
            evaluation=evaluation,
            comparison=None,
            suggested_questions=_build_general_followups("财报解读", snapshot, analysis),
            context_used=context_used,
            context_company_name=context_company_name,
            context_stock_code=context_stock_code,
        )

    steps.append(AgentStep(step_name="公司识别与数据抓取", status="failed", summary="未识别到有效 A 股公司", tool_name="build_company_snapshot", error=snapshot.get("data_warning", "not_found")))
    analysis = registry.call("analyze_general_question", effective_query)
    tool_calls.append(ToolCallResult(tool_name="analyze_general_question", success=True, summary=analysis.ai_status))
    steps.append(AgentStep(step_name="通用问题解读", status="success", summary="未识别到具体公司，已切换为通用问题模式", tool_name="analyze_general_question"))
    warnings.append("未识别到具体公司，当前输出为通用财报解读建议。可补充公司名或代码获得更精准结果。")
    general_snapshot = {
        "found": True,
        "company_name": "通用问题模式",
        "stock_code": "N/A",
        "data_source": "general_guidance",
        "data_warning": "",
        "data_quality": {"live_metric_count": 0, "fallback_enabled": True, "report_period": "general"},
        "financial_metrics": {
            "report_period": "通用方法论",
            "revenue": "请补充具体公司",
            "net_profit": "请补充具体公司",
            "operating_cash_flow": "请补充具体公司",
            "revenue_yoy": "请补充具体公司",
            "net_profit_yoy": "请补充具体公司",
        },
        "cash_flow_summary": "当前为通用问题模式，未绑定具体公司财务数据。",
        "management_outlook": "请补充行业或公司，以便给出更精准展望。",
        "daily_prices": [],
        "price_warning": "通用问题模式不展示个股日线走势。",
        "candidates": snapshot.get("candidates", []),
    }
    evaluation = _evaluate_output(general_snapshot, analysis)
    return AgentResult(
        query=query,
        resolved_query=effective_query,
        intent="通用财报问答",
        steps=steps,
        tool_calls=tool_calls,
        analysis=analysis,
        snapshot=general_snapshot,
        warnings=warnings,
        data_quality=general_snapshot.get("data_quality", {}),
        evaluation=evaluation,
        comparison=None,
        suggested_questions=_build_general_followups("通用财报问答", general_snapshot, analysis),
        context_used=context_used,
        context_company_name=context_company_name,
        context_stock_code=context_stock_code,
    )
