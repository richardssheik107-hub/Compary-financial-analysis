from __future__ import annotations

import json
import os
import re
from typing import Any

from src.net_utils import is_proxy_error, temporary_disable_proxy
from src.models import AnalysisResult, Scores


def analyze_general_question(user_question: str) -> AnalysisResult:
    question = (user_question or "").strip() or "财报怎么看"
    return AnalysisResult(
        plain_cashflow_summary=(
            f"你这个问题（{question}）如果不绑定具体公司，可以先按一个顺序看："
            "先看收入是否持续增长，再看净利润是否和收入同方向变化，最后看经营现金流是否能跟上利润。"
            "如果利润在涨但现金流跟不上，通常要更谨慎。"
        ),
        future_outlook=(
            "下一步建议你补充一个具体公司名称或6位股票代码。"
            "这样我可以把同样的方法落到真实财报数据上，给出更有针对性的解释和风险提示。"
        ),
        scores=Scores(profitability=7.0, cash_saving=7.0, future_potential=6.5),
        sentiment_label="中性偏稳",
        risk_notes="股票投资有风险，不构成投资建议。",
        ai_status="通用问题模式",
    )


SYSTEM_PROMPT = """
你是“大白话财报”的 AI 财报解读员，风格像一个接地气但非常谨慎的财经博主。

你的任务：
1. 把财报数据解释给没有金融背景的普通用户。
2. 多用生活化比喻，少用专业术语；如果必须使用术语，要顺手解释。
3. 不输出任何直接交易指令，不说“买入”“卖出”“重仓”“梭哈”“满仓”“清仓”。
4. 不承诺收益，不预测股价，不制造焦虑或冲动。
5. 明确说明内容仅用于学习和理解财报，不构成投资建议。
6. 只输出 JSON，不输出 Markdown，不添加 JSON 之外的文字。
"""

REQUIRED_KEYS = {
    "plain_cashflow_summary",
    "future_outlook",
    "scores",
    "sentiment_label",
    "risk_notes",
}

STANDARD_RISK_NOTE = "股票投资有风险，不构成投资建议。"

FORBIDDEN_REPLACEMENTS = {
    "买入": "关注",
    "卖出": "回避冲动操作",
    "重仓": "提高关注度",
    "满仓": "保持仓位克制",
    "清仓": "重新评估风险",
    "梭哈": "保持冷静",
}


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

    profitability = 7.0
    if profit_yoy is not None:
        profitability = 6.5 + max(-2.0, min(2.0, profit_yoy / 20))

    cash_saving = 7.0
    if cash_flow is not None and net_profit is not None and net_profit > 0:
        ratio = cash_flow / net_profit
        cash_saving = 6.5 + max(-2.0, min(2.0, ratio - 1))

    future_potential = 6.5
    if revenue_yoy is not None:
        future_potential = 6.0 + max(-1.5, min(2.0, revenue_yoy / 25))

    return Scores(
        profitability=max(0.0, min(10.0, round(profitability, 1))),
        cash_saving=max(0.0, min(10.0, round(cash_saving, 1))),
        future_potential=max(0.0, min(10.0, round(future_potential, 1))),
    )


def _fallback_sentiment(scores: Scores) -> str:
    average = (scores.profitability + scores.cash_saving + scores.future_potential) / 3
    if average >= 8:
        return "偏乐观但需观察"
    if average >= 6.5:
        return "中性偏稳"
    if average >= 5:
        return "偏谨慎"
    return "谨慎观察"


def _fallback_analysis(snapshot: dict[str, Any], reason: str) -> AnalysisResult:
    metrics = snapshot.get("financial_metrics", {})
    company = snapshot.get("company_name", "这家公司")
    cash_flow = metrics.get("operating_cash_flow") or snapshot.get("cash_flow_summary") or "现金回款信息暂不完整"
    revenue = metrics.get("revenue") or "收入数据暂不完整"
    net_profit = metrics.get("net_profit") or "利润数据暂不完整"
    revenue_yoy = metrics.get("revenue_yoy") or "营收增速暂不完整"
    profit_yoy = metrics.get("net_profit_yoy") or "利润增速暂不完整"
    management_outlook = snapshot.get("management_outlook") or "管理层展望暂不完整"
    scores = _fallback_scores(metrics)

    return AnalysisResult(
        plain_cashflow_summary=f"{company}的账面故事要分开看：收入线索是{revenue}，利润线索是{net_profit}，现金流线索是{cash_flow}。如果收入不少但利润和现金跟不上，就像店里客人很多、真正留下的钱却有限，后续要重点看回款和成本压力。",
        future_outlook=f"未来一年要看增长质量，而不只看规模。当前收入线索是{revenue}，营收同比为{revenue_yoy}；利润线索是{net_profit}，利润同比为{profit_yoy}；现金流是{cash_flow}。结合管理层说法：{management_outlook} 如果收入继续扩张、利润和现金能同步跟上，发展势头会更稳；反过来就要谨慎看待增长含金量。",
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


def _sanitize_advice(text: str) -> str:
    cleaned = text
    for forbidden, safe in FORBIDDEN_REPLACEMENTS.items():
        cleaned = cleaned.replace(forbidden, safe)
    return cleaned


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
    risk_notes = STANDARD_RISK_NOTE
    if "不构成投资建议" in raw_risk_notes:
        risk_notes = STANDARD_RISK_NOTE
    elif raw_risk_notes and STANDARD_RISK_NOTE not in raw_risk_notes:
        risk_notes = f"{raw_risk_notes.rstrip('。')}。{STANDARD_RISK_NOTE}"

    return AnalysisResult(
        plain_cashflow_summary=_sanitize_advice(str(payload["plain_cashflow_summary"])),
        future_outlook=_sanitize_advice(str(payload["future_outlook"])),
        scores=Scores(
            profitability=_coerce_score(scores.get("profitability"), 7.0),
            cash_saving=_coerce_score(scores.get("cash_saving"), 7.0),
            future_potential=_coerce_score(scores.get("future_potential"), 6.5),
        ),
        sentiment_label=_sanitize_advice(str(payload["sentiment_label"])),
        risk_notes=_sanitize_advice(risk_notes),
        ai_status=ai_status,
    )


def _ensure_plain_summary_detail(result: AnalysisResult, snapshot: dict[str, Any]) -> AnalysisResult:
    if len(result.plain_cashflow_summary) >= 80:
        return result

    metrics = snapshot.get("financial_metrics", {})
    revenue = metrics.get("revenue") or "收入暂不完整"
    net_profit = metrics.get("net_profit") or "利润暂不完整"
    cash_flow = metrics.get("operating_cash_flow") or "现金流暂不完整"
    addition = (
        f"再看三项：收入{revenue}，利润{net_profit}，现金流{cash_flow}；"
        "三者合在一起，才能看出钱是不是真留在公司手里。"
    )
    result.plain_cashflow_summary = _sanitize_advice(f"{result.plain_cashflow_summary}{addition}")
    return result


def _ensure_future_outlook_detail(result: AnalysisResult, snapshot: dict[str, Any]) -> AnalysisResult:
    weak_phrases = ["不明朗", "还需关注", "暂时不明朗", "需要观察"]
    if len(result.future_outlook) >= 90 and not any(phrase in result.future_outlook for phrase in weak_phrases):
        return result

    metrics = snapshot.get("financial_metrics", {})
    revenue = metrics.get("revenue") or "收入暂不完整"
    net_profit = metrics.get("net_profit") or "利润暂不完整"
    cash_flow = metrics.get("operating_cash_flow") or "现金流暂不完整"
    revenue_yoy = metrics.get("revenue_yoy") or "营收增速暂不完整"
    profit_yoy = metrics.get("net_profit_yoy") or "利润增速暂不完整"
    management_outlook = snapshot.get("management_outlook") or "管理层展望暂不完整"
    result.future_outlook = _sanitize_advice(
        f"未来一年要看增长是不是有含金量。收入是{revenue}，营收同比{revenue_yoy}，说明规模变化要继续跟踪；"
        f"利润是{net_profit}，利润同比{profit_yoy}，现金流是{cash_flow}，这决定增长能不能变成手里的钱。"
        f"管理层展望提到：{management_outlook} 因此更适合看需求、成本和回款三件事是否同步改善。"
    )
    return result


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

输出必须是合法 JSON，字段必须完整：
{{
  "plain_cashflow_summary": "白话解读，100字左右，写2到3句，不要少于80个汉字。必须同时解释收入、利润、现金流三者关系，用生活化比喻说明公司到底是赚到钱、账面好看，还是现金压力较大",
  "future_outlook": "未来一年分析，90到130个汉字，写2到3句。必须结合收入、营收同比、利润、利润同比、现金流和管理层展望，说明发展势头和需要观察的关键变量，不能只说不明朗，避免股价预测",
  "scores": {{
    "profitability": 0到10之间的数字,
    "cash_saving": 0到10之间的数字,
    "future_potential": 0到10之间的数字
  }},
  "sentiment_label": "极度乐观/偏乐观/中性偏稳/偏谨慎/谨慎观察 之一或相近表达",
  "risk_notes": "必须包含：股票投资有风险，不构成投资建议"
}}
"""


def _call_openai(client: Any, model: str, messages: list[dict[str, str]]) -> str:
    def _request() -> str:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.35,
                response_format={"type": "json_object"},
            )
        except Exception as exc:
            if "response_format" not in str(exc):
                raise
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.35,
            )
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
        result = _parse_result(payload, f"真实 API：{model}")
        result = _ensure_plain_summary_detail(result, snapshot)
        return _ensure_future_outlook_detail(result, snapshot)
    except Exception as exc:
        return _fallback_analysis(snapshot, f"AI API 调用失败：{exc}")
