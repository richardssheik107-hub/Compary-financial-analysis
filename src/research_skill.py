from __future__ import annotations

import json
import os
from dataclasses import replace
from typing import Any

from src.net_utils import is_proxy_error, temporary_disable_proxy
from src.research_models import ResearchResult, SourceNote

SKILL_PROMPT = """
你是上市公司经营研究写作助手。你需要把已有研究结论润色成更通顺、更有逻辑的中文。
约束：
1) 不得输出买卖建议、目标价、仓位建议；
2) 每段先结论，再证据，再限制；
3) 不能编造不存在的数据，无法确认的内容用“模型推断”表述；
4) 输出必须是 JSON。
"""


def _call_openai(client: Any, model: str, messages: list[dict[str, str]]) -> str:
    def _request() -> str:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.25,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content or "{}"

    try:
        return _request()
    except Exception as exc:
        if not is_proxy_error(exc):
            raise
        with temporary_disable_proxy():
            return _request()


def _extract_json(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


def _sanitize(text: str) -> str:
    banned = {
        "买入": "关注",
        "卖出": "谨慎观察",
        "满仓": "控制仓位",
        "清仓": "重新评估",
        "梭哈": "保持克制",
        "目标价": "估值区间",
    }
    output = (text or "").strip()
    for k, v in banned.items():
        output = output.replace(k, v)
    return output


def _quality_gate_text(text: str) -> str:
    value = _sanitize(text).replace("。。", "。").replace("，，", "，").strip()
    if len(value) > 8 and not value.endswith(("。", "！", "？")):
        value = f"{value}。"
    return value


def _as_text(value: Any, fallback: str) -> str:
    if value is None:
        return fallback
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("text", "conclusion", "answer", "content"):
            if key in value and isinstance(value[key], str):
                return value[key]
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        parts = [item for item in value if isinstance(item, str)]
        if parts:
            return " ".join(parts)
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _quality_gate_result(result: ResearchResult) -> ResearchResult:
    return replace(
        result,
        one_line_conclusion=_quality_gate_text(result.one_line_conclusion),
        business_overview=_quality_gate_text(result.business_overview),
        operating_performance=_quality_gate_text(result.operating_performance),
        profitability_quality=_quality_gate_text(result.profitability_quality),
        cashflow_quality=_quality_gate_text(result.cashflow_quality),
        growth_and_industry=_quality_gate_text(result.growth_and_industry),
        major_risks=_quality_gate_text(result.major_risks),
    )


def _local_refine(result: ResearchResult) -> ResearchResult:
    return _quality_gate_result(result)


def refine_research_result(result: ResearchResult, query: str) -> ResearchResult:
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    base_url = os.getenv("OPENAI_BASE_URL") or None
    if not api_key or api_key == "your_api_key_here":
        return _local_refine(result)

    try:
        from openai import OpenAI
    except Exception:
        return _local_refine(result)

    payload = {
        "query": query,
        "report_type": result.report_type,
        "title": result.title,
        "one_line_conclusion": result.one_line_conclusion,
        "business_overview": result.business_overview,
        "operating_performance": result.operating_performance,
        "profitability_quality": result.profitability_quality,
        "cashflow_quality": result.cashflow_quality,
        "growth_and_industry": result.growth_and_industry,
        "major_risks": result.major_risks,
        "limitations": result.limitations,
    }
    user_prompt = f"""请润色以下研究输出，增强逻辑与可读性，保持事实不变：\n{json.dumps(payload, ensure_ascii=False)}\n
输出 JSON 字段：one_line_conclusion, business_overview, operating_performance, profitability_quality, cashflow_quality, growth_and_industry, major_risks
"""
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        content = _call_openai(
            client,
            model,
            [
                {"role": "system", "content": SKILL_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
        data = _extract_json(content)
        refined = replace(
            result,
            one_line_conclusion=_as_text(data.get("one_line_conclusion"), result.one_line_conclusion),
            business_overview=_as_text(data.get("business_overview"), result.business_overview),
            operating_performance=_as_text(data.get("operating_performance"), result.operating_performance),
            profitability_quality=_as_text(data.get("profitability_quality"), result.profitability_quality),
            cashflow_quality=_as_text(data.get("cashflow_quality"), result.cashflow_quality),
            growth_and_industry=_as_text(data.get("growth_and_industry"), result.growth_and_industry),
            major_risks=_as_text(data.get("major_risks"), result.major_risks),
            source_notes=[
                *result.source_notes,
                SourceNote(source_type="模型推理", title="research_skill", detail=f"润色模型：{model}"),
            ],
        )
        return _quality_gate_result(refined)
    except Exception:
        return _local_refine(result)
