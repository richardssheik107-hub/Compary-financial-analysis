from __future__ import annotations

import json
import os
import re
from typing import Any

from src.models import AnalysisResult, Scores
from src.net_utils import is_proxy_error, temporary_disable_proxy

SYSTEM_PROMPT = """
你是“大白话财报”的 AI 财报解读助手。
要求：
1) 用通顺、克制、具体的中文表达；
2) 必须解释收入、利润、现金流之间的关系；
3) 禁止给出买卖建议和股价预测；
4) 输出必须是 JSON。
"""

REQUIRED_KEYS = {"plain_cashflow_summary", "future_outlook", "scores", "sentiment_label", "risk_notes"}
STANDARD_RISK_NOTE = "股票投资有风险，不构成投资建议。"
FORBIDDEN_REPLACEMENTS = {
    "买入": "关注",
    "卖出": "避免冲动操作",
    "重仓": "提高关注度",
    "满仓": "保持仓位克制",
    "清仓": "重新评估风险",
    "梭哈": "保持冷静",
}


def analyze_general_question(user_question: str) -> AnalysisResult:
    question = (user_question or "").strip() or "财报怎么看"
    return AnalysisResult(
        plain_cashflow_summary=(
            f"针对“{question}”这类未绑定公司的问题，建议先看三件事：收入是否持续增长、利润是否和收入同向变化、经营现金流是否能匹配利润。"
            "如果利润增长但现金流跟不上，通常要更谨慎，因为这可能意味着增长质量还不够扎实。"
        ),
        future_outlook=(
            "下一步建议补充一个具体公司名称或 6 位股票代码。拿到真实财报后，可以按季度跟踪收入增速、利润增速与经营现金流是否同步改善，"
            "并结合行业景气和管理层表述，判断当前变化是短期扰动还是中期趋势。"
        ),
        scores=Scores(profitability=7.0, cash_saving=7.0, future_potential=6.5),
        sentiment_label="中性偏稳",
        risk_notes=STANDARD_RISK_NOTE,
        ai_status="通用问题模式",
    )


def _extract_number(text: Any) -> float | None:
    if text is None:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", str(text).replace(",", ""))
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _fallback_scores(metrics: dict[str, Any]) -> Scores:
    revenue_yoy = _extract_number(metrics.get("revenue_yoy"))
    profit_yoy = _extract_number(metrics.get("net_profit_yoy"))
    cash_flow = _extract_number(metrics.get("operating_cash_flow"))
    net_profit = _extract_number(metrics.get("net_profit"))

    profitability = 7.0 if profit_yoy is None else 6.5 + max(-2.0, min(2.0, profit_yoy / 20))
    cash_saving = 7.0
    if cash_flow is not None and net_profit is not None and net_profit > 0:
        ratio = cash_flow / net_profit
        cash_saving = 6.5 + max(-2.0, min(2.0, ratio - 1))
    future_potential = 6.5 if revenue_yoy is None else 6.0 + max(-1.5, min(2.0, revenue_yoy / 25))

    return Scores(
        profitability=max(0.0, min(10.0, round(profitability, 1))),
        cash_saving=max(0.0, min(10.0, round(cash_saving, 1))),
        future_potential=max(0.0, min(10.0, round(future_potential, 1))),
    )


def _fallback_sentiment(scores: Scores) -> str:
    avg = (scores.profitability + scores.cash_saving + scores.future_potential) / 3
    if avg >= 8:
        return "偏乐观但需观察"
    if avg >= 6.5:
        return "中性偏稳"
    if avg >= 5:
        return "偏谨慎"
    return "谨慎观察"


def _sanitize_advice(text: str) -> str:
    cleaned = text or ""
    for forbidden, safe in FORBIDDEN_REPLACEMENTS.items():
        cleaned = cleaned.replace(forbidden, safe)
    return cleaned


def _polish_text(text: str, min_len: int) -> str:
    cleaned = _sanitize_advice((text or "").strip())
    cleaned = re.sub(r"\s+", "", cleaned)
    cleaned = (
        cleaned.replace("，，", "，")
        .replace("。。", "。")
        .replace("：：", "：")
        .replace("；；", "；")
    )
    if cleaned and cleaned[-1] not in "。！？":
        cleaned += "。"
    if len(cleaned) < min_len:
        cleaned += "建议结合下一期财报，持续跟踪收入、利润和现金流是否同向改善。"
    return cleaned


def _fallback_analysis(snapshot: dict[str, Any], reason: str) -> AnalysisResult:
    metrics = snapshot.get("financial_metrics", {})
    company = snapshot.get("company_name", "这家公司")
    cash_flow = metrics.get("operating_cash_flow") or snapshot.get("cash_flow_summary") or "现金流信息暂不完整"
    revenue = metrics.get("revenue") or "收入数据暂不完整"
    net_profit = metrics.get("net_profit") or "利润数据暂不完整"
    revenue_yoy = metrics.get("revenue_yoy") or "营收增速暂不完整"
    profit_yoy = metrics.get("net_profit_yoy") or "利润增速暂不完整"
    management_outlook = snapshot.get("management_outlook") or "管理层展望暂不完整"
    scores = _fallback_scores(metrics)

    summary = (
        f"{company}的经营质量要把收入、利润和现金流一起看。当前收入为{revenue}，净利润为{net_profit}，经营现金流为{cash_flow}。"
        "如果收入在增长，但利润和现金流没有同步改善，就要警惕增长含金量不足。"
    )
    outlook = (
        f"未来一年建议重点看三件事：营收同比（{revenue_yoy}）能否持续、净利润同比（{profit_yoy}）是否跟上、现金流是否保持健康。"
        f"结合管理层表述（{management_outlook}），如果三项同向改善，趋势会更稳。"
    )

    return AnalysisResult(
        plain_cashflow_summary=_polish_text(summary, min_len=80),
        future_outlook=_polish_text(outlook, min_len=90),
        scores=scores,
        sentiment_label=_fallback_sentiment(scores),
        risk_notes=f"本段为本地兜底解读，原因：{reason}。{STANDARD_RISK_NOTE}",
        ai_status=f"本地兜底：{reason}",
    )


def _extract_json(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if not match:
            raise
        return json.loads(match.group(0))


def _coerce_score(value: Any, default: float) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(10.0, round(score, 1)))


def _validate_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("AI output is not a JSON object.")
    missing = REQUIRED_KEYS - set(payload)
    if missing:
        raise ValueError(f"AI output missing required fields: {', '.join(sorted(missing))}")
    if not isinstance(payload.get("scores"), dict):
        raise ValueError("AI output field 'scores' must be an object.")
    return payload


def _parse_result(payload: dict[str, Any], ai_status: str) -> AnalysisResult:
    payload = _validate_payload(payload)
    scores = payload["scores"]
    raw_risk_notes = str(payload.get("risk_notes") or "")
    if "不构成投资建议" in raw_risk_notes:
        risk_notes = STANDARD_RISK_NOTE
    elif raw_risk_notes:
        risk_notes = f"{raw_risk_notes.rstrip('。')}。{STANDARD_RISK_NOTE}"
    else:
        risk_notes = STANDARD_RISK_NOTE

    return AnalysisResult(
        plain_cashflow_summary=_polish_text(str(payload["plain_cashflow_summary"]), min_len=80),
        future_outlook=_polish_text(str(payload["future_outlook"]), min_len=90),
        scores=Scores(
            profitability=_coerce_score(scores.get("profitability"), 7.0),
            cash_saving=_coerce_score(scores.get("cash_saving"), 7.0),
            future_potential=_coerce_score(scores.get("future_potential"), 6.5),
        ),
        sentiment_label=_sanitize_advice(str(payload["sentiment_label"])),
        risk_notes=_sanitize_advice(risk_notes),
        ai_status=ai_status,
    )


def _build_user_prompt(snapshot: dict[str, Any], user_question: str) -> str:
    llm_input = {
        "company_name": snapshot["company_name"],
        "stock_code": snapshot["stock_code"],
        "financial_metrics": snapshot["financial_metrics"],
        "cash_flow_summary": snapshot["cash_flow_summary"],
        "management_outlook": snapshot["management_outlook"],
        "data_source": snapshot["data_source"],
        "data_quality": snapshot["data_quality"],
        "user_question": user_question,
    }
    return f"""
请基于以下结构化数据生成财报白话分析：
{json.dumps(llm_input, ensure_ascii=False, indent=2)}

输出必须是合法 JSON，字段完整：
{{
  "plain_cashflow_summary": "80到140字，必须出现收入、利润、现金流，并给出关系解释",
  "future_outlook": "90到160字，给出未来一年观察点，不预测股价",
  "scores": {{
    "profitability": 0到10数字,
    "cash_saving": 0到10数字,
    "future_potential": 0到10数字
  }},
  "sentiment_label": "偏乐观/中性偏稳/偏谨慎等",
  "risk_notes": "必须包含：股票投资有风险，不构成投资建议"
}}
"""


def _call_openai(client: Any, model: str, messages: list[dict[str, str]]) -> str:
    def _request() -> str:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.3,
                response_format={"type": "json_object"},
            )
        except Exception as exc:
            if "response_format" not in str(exc):
                raise
            response = client.chat.completions.create(model=model, messages=messages, temperature=0.3)
        return response.choices[0].message.content or "{}"

    try:
        return _request()
    except Exception as exc:
        if not is_proxy_error(exc):
            raise
        with temporary_disable_proxy():
            return _request()


def analyze_company(snapshot: dict[str, Any], user_question: str) -> AnalysisResult:
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    base_url = os.getenv("OPENAI_BASE_URL") or None

    if not api_key or api_key == "your_api_key_here":
        return _fallback_analysis(snapshot, "未配置 OPENAI_API_KEY")

    try:
        from openai import OpenAI
    except ImportError:
        return _fallback_analysis(snapshot, "未安装 openai 依赖，请运行 start.bat 安装 requirements.txt")

    client = OpenAI(api_key=api_key, base_url=base_url)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": _build_user_prompt(snapshot, user_question)},
    ]

    try:
        content = _call_openai(client, model, messages)
        payload = _extract_json(content)
        return _parse_result(payload, f"真实 API：{model}")
    except Exception as exc:
        return _fallback_analysis(snapshot, f"AI API 调用失败：{exc}")
