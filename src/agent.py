from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Callable

from src.ai_client import analyze_company, analyze_general_question
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


def _detect_intent(query: str) -> str:
    normalized = query.strip()
    if not normalized:
        return "未提供问题"
    if any(keyword in normalized for keyword in ["对比", "比较", "谁更好"]):
        return "财报对比"
    if any(keyword in normalized for keyword in ["风险", "亏损", "压力"]):
        return "风险分析"
    if any(keyword in normalized for keyword in ["现金流", "赚不赚钱", "利润", "营收"]):
        return "财报解读"
    return "通用财报问答"


def _has_explicit_target(query: str) -> bool:
    if re.search(r"\b\d{6}\b", query):
        return True
    return any(token in query for token in ["茅台", "宁德", "平安银行", "万科", "格力", "比亚迪", "招商银行"])


def _apply_context_to_query(query: str, context_company_name: str, context_stock_code: str) -> tuple[str, bool]:
    normalized = (query or "").strip()
    if not normalized:
        return normalized, False
    if not (context_company_name or context_stock_code):
        return normalized, False
    if _has_explicit_target(normalized):
        return normalized, False
    followup_signals = ["它", "这家公司", "这家", "上一家", "刚才这家", "继续", "再看", "进一步", "那它"]
    if any(signal in normalized for signal in followup_signals):
        target = context_company_name or context_stock_code
        return f"{target}，{normalized}", True
    generic_question_signals = ["怎么看", "如何", "风险", "利润", "现金流", "营收", "增速", "估值", "还能"]
    if len(normalized) <= 28 or any(signal in normalized for signal in generic_question_signals):
        target = context_company_name or context_stock_code
        return f"{target}，{normalized}", True
    return normalized, False


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


def _extract_compare_targets(query: str) -> list[str]:
    cleaned = re.sub(r"[，。？！,.!?]", " ", query)
    cleaned = re.sub(r"(帮我|看看|最近|怎么样|未来|财报|分析|一下|请|一下子)", " ", cleaned)
    parts = re.split(r"(?:对比|比较|谁更好|和|与|跟|vs|VS)", cleaned)
    candidates = [part.strip() for part in parts if part and part.strip()]
    unique: list[str] = []
    for candidate in candidates:
        if candidate not in unique:
            unique.append(candidate)
    return unique[:4]


def _to_float_metric(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).replace("约", "").replace("亿元", "").replace("%", "").replace(",", "").strip()
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _build_compare_summary(snapshot_a: dict[str, Any], snapshot_b: dict[str, Any], analysis_a: Any, analysis_b: Any) -> dict[str, Any]:
    metrics_a = snapshot_a.get("financial_metrics", {})
    metrics_b = snapshot_b.get("financial_metrics", {})
    score_a = round((analysis_a.scores.profitability + analysis_a.scores.cash_saving + analysis_a.scores.future_potential) / 3, 2)
    score_b = round((analysis_b.scores.profitability + analysis_b.scores.cash_saving + analysis_b.scores.future_potential) / 3, 2)
    revenue_yoy_a = _to_float_metric(metrics_a.get("revenue_yoy"))
    revenue_yoy_b = _to_float_metric(metrics_b.get("revenue_yoy"))
    profit_yoy_a = _to_float_metric(metrics_a.get("net_profit_yoy"))
    profit_yoy_b = _to_float_metric(metrics_b.get("net_profit_yoy"))

    winner = snapshot_a.get("company_name", "公司A")
    reason = "综合评分更高"
    if score_b > score_a:
        winner = snapshot_b.get("company_name", "公司B")
    if revenue_yoy_a is not None and revenue_yoy_b is not None and profit_yoy_a is not None and profit_yoy_b is not None:
        growth_a = revenue_yoy_a + profit_yoy_a
        growth_b = revenue_yoy_b + profit_yoy_b
        if growth_b > growth_a:
            winner = snapshot_b.get("company_name", "公司B")
            reason = "营收和利润增速合计更强"
        elif growth_a > growth_b:
            winner = snapshot_a.get("company_name", "公司A")
            reason = "营收和利润增速合计更强"

    confidence_score = 82
    limitations: list[str] = []
    if snapshot_a.get("data_source", "").startswith("sample") or snapshot_b.get("data_source", "").startswith("sample"):
        confidence_score -= 12
        limitations.append("部分指标来自样例兜底，真实度低于全量实时财务摘要。")
    if metrics_a.get("report_period") != metrics_b.get("report_period"):
        confidence_score -= 8
        limitations.append("两家公司报告期可能不一致，对比结论需结合同口径时间窗口复核。")
    if snapshot_a.get("price_warning") or snapshot_b.get("price_warning"):
        confidence_score -= 5
        limitations.append("近期行情数据不完整，价格趋势维度仅供参考。")
    confidence_score = max(40, min(95, confidence_score))
    followups = [
        f"继续对比 {snapshot_a.get('company_name', '公司A')} 和 {snapshot_b.get('company_name', '公司B')} 的毛利率与净利率变化。",
        "补充查看最近两期财报，确认营收增长是否伴随现金流同步改善。",
        "针对领先公司继续追问：增长持续性最大的风险来自哪里。",
    ]

    return {
        "is_compare": True,
        "company_a": {"name": snapshot_a.get("company_name", ""), "code": snapshot_a.get("stock_code", ""), "score": score_a},
        "company_b": {"name": snapshot_b.get("company_name", ""), "code": snapshot_b.get("stock_code", ""), "score": score_b},
        "winner": winner,
        "winner_reason": reason,
        "industry_context": "当前结论主要基于财报核心指标与 AI 解读，不等同于完整行业景气度或估值判断。",
        "confidence_score": confidence_score,
        "limitations": limitations,
        "followups": followups,
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
            f"把 {company} 和同业龙头做一版核心指标对比。",
        ]
    if analysis is not None:
        return [
            "请把刚才结论改写成三条可执行的观察清单。",
            "再给我一个更保守视角下的风险复盘。",
        ]
    return []


def run_financial_agent(query: str, *, resolved_query: str | None = None, context_company_name: str = "", context_stock_code: str = "", context_used: bool = False) -> AgentResult:
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

    if not query.strip():
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

    if intent == "财报对比":
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
                steps.append(
                    AgentStep(
                        step_name="对比目标识别",
                        status="success",
                        summary=f"已识别目标：{snapshot.get('company_name')} ({snapshot.get('stock_code')})",
                        tool_name="build_company_snapshot",
                    )
                )
            if len(snapshots) == 2:
                break

        if len(snapshots) < 2:
            steps.append(
                AgentStep(
                    step_name="对比分析",
                    status="failed",
                    summary="未能识别两个有效公司，无法生成对比结果",
                    tool_name="build_company_snapshot",
                    error="compare_targets_not_enough",
                )
            )
            warnings.append("对比问题需要两个可识别的 A 股公司，例如：宁德时代和比亚迪谁更好。")
            return AgentResult(
                query=query,
                resolved_query=effective_query,
                intent=intent,
                steps=steps,
                tool_calls=tool_calls,
                analysis=None,
                snapshot={"found": False, "data_warning": "未识别到两个可对比公司。"},
                warnings=warnings,
                data_quality={},
                evaluation=None,
                comparison=None,
                suggested_questions=[
                    "试试：宁德时代和比亚迪谁更好？",
                    "试试：平安银行和招商银行谁的增长质量更稳？",
                ],
                context_used=context_used,
                context_company_name=context_company_name,
                context_stock_code=context_stock_code,
            )

        for snapshot in snapshots:
            analysis = registry.call("analyze_company", snapshot, effective_query)
            analyses.append(analysis)
            tool_calls.append(ToolCallResult(tool_name="analyze_company", success=True, summary=f"{snapshot.get('company_name')} -> {analysis.ai_status}"))

        steps.append(
            AgentStep(
                step_name="对比结论生成",
                status="success",
                summary=f"已完成 {snapshots[0].get('company_name')} 与 {snapshots[1].get('company_name')} 对比",
                tool_name="compare_synthesizer",
            )
        )
        comparison = _build_compare_summary(snapshots[0], snapshots[1], analyses[0], analyses[1])
        # Keep single-company rendering path compatible by returning company A's snapshot/analysis.
        evaluation = _evaluate_output(snapshots[0], analyses[0])
        return AgentResult(
            query=query,
            resolved_query=effective_query,
            intent=intent,
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
    tool_calls.append(
        ToolCallResult(
            tool_name="build_company_snapshot",
            success=bool(snapshot.get("found")),
            summary=f"found={snapshot.get('found')} source={snapshot.get('data_source', 'unknown')}",
            error="" if snapshot.get("found") else snapshot.get("data_warning", "not_found"),
        )
    )
    if snapshot.get("found"):
        company = f"{snapshot.get('company_name', '未知公司')} ({snapshot.get('stock_code', '-')})"
        steps.append(AgentStep(step_name="公司识别与数据抓取", status="success", summary=f"已识别目标：{company}", tool_name="build_company_snapshot"))
    else:
        steps.append(
            AgentStep(
                step_name="公司识别与数据抓取",
                status="failed",
                summary="未识别到有效 A 股公司",
                tool_name="build_company_snapshot",
                error=snapshot.get("data_warning", "not_found"),
            )
        )
        # General-question mode: if no company was detected, still return a useful educational answer.
        analysis = registry.call("analyze_general_question", effective_query)
        tool_calls.append(
            ToolCallResult(
                tool_name="analyze_general_question",
                success=True,
                summary=analysis.ai_status,
                error="",
            )
        )
        steps.append(
            AgentStep(
                step_name="通用问题解读",
                status="success",
                summary="未识别到具体公司，已切换为通用问题模式",
                tool_name="analyze_general_question",
            )
        )
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

    analysis = registry.call("analyze_company", snapshot, effective_query)
    tool_calls.append(
        ToolCallResult(
            tool_name="analyze_company",
            success=True,
            summary=analysis.ai_status,
            error="",
        )
    )
    steps.append(AgentStep(step_name="财报解读生成", status="success", summary=f"解读完成：{analysis.ai_status}", tool_name="analyze_company"))

    if snapshot.get("data_warning"):
        warnings.append(snapshot["data_warning"])
    if snapshot.get("price_warning"):
        warnings.append(snapshot["price_warning"])
    evaluation = _evaluate_output(snapshot, analysis)

    return AgentResult(
        query=query,
        resolved_query=effective_query,
        intent=intent,
        steps=steps,
        tool_calls=tool_calls,
        analysis=analysis,
        snapshot=snapshot,
        warnings=warnings,
        data_quality=snapshot.get("data_quality", {}),
        evaluation=evaluation,
        comparison=None,
        suggested_questions=_build_general_followups(intent, snapshot, analysis),
        context_used=context_used,
        context_company_name=context_company_name,
        context_stock_code=context_stock_code,
    )
