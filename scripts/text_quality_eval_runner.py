from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402
from src.research_agent import run_company_research_agent  # noqa: E402

TESTSET = ROOT / "eval" / "research_testset.csv"
DETAIL_CSV = ROOT / "eval" / "text_quality_baseline.csv"
SUMMARY_MD = ROOT / "eval" / "text_quality_baseline_summary.md"


@dataclass
class QualityRow:
    case_id: str
    query: str
    expected_route: str
    actual_route: str
    route_ok: bool
    relevance_score: int
    structure_score: int
    evidence_score: int
    logic_score: int
    expression_score: int
    total_score: int
    quality_pass: bool
    empty_talk: bool
    logic_issue: bool
    source_used: bool
    answer_length: int
    source_count: int
    error: str = ""


def _result_text(result: Any) -> str:
    fields = [
        result.one_line_conclusion,
        result.business_overview,
        result.operating_performance,
        result.profitability_quality,
        result.cashflow_quality,
        result.growth_and_industry,
        result.major_risks,
        " ".join(result.tracking_checklist or []),
    ]
    return " ".join(str(item) for item in fields if item)


def _contains_any(text: str, words: list[str]) -> bool:
    return any(word in text for word in words)


def _score_relevance(query: str, text: str) -> int:
    normalized = re.sub(r"\s+", "", query)
    keywords = [item for item in re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,}", normalized) if len(item) >= 2]
    if not keywords:
        return 12
    hit = sum(1 for item in keywords[:6] if item in text)
    return min(20, 8 + hit * 3)


def _score_structure(result: Any) -> int:
    fields = [
        result.one_line_conclusion,
        result.business_overview,
        result.operating_performance,
        result.profitability_quality,
        result.cashflow_quality,
        result.growth_and_industry,
        result.major_risks,
    ]
    score = sum(2 for item in fields if str(item).strip())
    if len(result.tracking_checklist or []) >= 3:
        score += 6
    return min(20, score)


def _score_evidence(result: Any) -> int:
    score = 0
    if result.source_notes:
        score += 8
    if result.evidence_by_section:
        score += 8
    source_summary = result.source_summary or {}
    if int(source_summary.get("total", 0)) > 0:
        score += 4
    elif any("模型" in str(note.source_type) or "财务" in str(note.source_type) for note in result.source_notes):
        score += 2
    return min(20, score)


def _has_logic_issue(text: str) -> bool:
    contradiction_pairs = [
        ("现金流弱", "现金流质量好"),
        ("资料不足", "确定"),
        ("无法判断", "明显优于"),
        ("不构成投资建议", "买入"),
        ("不构成投资建议", "卖出"),
    ]
    return any(a in text and b in text for a, b in contradiction_pairs)


def _score_logic(text: str) -> int:
    if _has_logic_issue(text):
        return 8
    if _contains_any(text, ["模型推断", "资料不足", "需", "建议", "风险"]):
        return 18
    return 15


def _empty_talk(text: str) -> bool:
    vague_words = ["综合来看", "持续关注", "较为稳健", "有待观察", "需要进一步分析"]
    metric_words = ["收入", "利润", "现金流", "风险", "业务", "增长", "财务"]
    return sum(text.count(w) for w in vague_words) >= 4 and not _contains_any(text, metric_words)


def _score_expression(text: str) -> int:
    forbidden = ["买入", "卖出", "满仓", "清仓", "梭哈", "目标价"]
    if _contains_any(text, forbidden):
        return 6
    score = 20
    if len(text) < 120:
        score -= 6
    if _empty_talk(text):
        score -= 6
    if "。。" in text or "，，" in text:
        score -= 3
    return max(0, min(20, score))


def _evaluate_case(row: dict[str, str]) -> QualityRow:
    case_id = row["case_id"]
    query = row["query"]
    expected_route = row["expected_route"]
    try:
        result = run_company_research_agent(query)
        text = _result_text(result)
        relevance = _score_relevance(query, text)
        structure = _score_structure(result)
        evidence = _score_evidence(result)
        logic = _score_logic(text)
        expression = _score_expression(text)
        total = relevance + structure + evidence + logic + expression
        source_count = len(result.source_notes or [])
        source_used = source_count > 0 or bool(result.evidence_by_section)
        return QualityRow(
            case_id=case_id,
            query=query,
            expected_route=expected_route,
            actual_route=result.report_type,
            route_ok=result.report_type == expected_route,
            relevance_score=relevance,
            structure_score=structure,
            evidence_score=evidence,
            logic_score=logic,
            expression_score=expression,
            total_score=total,
            quality_pass=total >= 80,
            empty_talk=_empty_talk(text),
            logic_issue=_has_logic_issue(text),
            source_used=source_used,
            answer_length=len(text),
            source_count=source_count,
        )
    except Exception as exc:
        return QualityRow(
            case_id=case_id,
            query=query,
            expected_route=expected_route,
            actual_route="error",
            route_ok=False,
            relevance_score=0,
            structure_score=0,
            evidence_score=0,
            logic_score=0,
            expression_score=0,
            total_score=0,
            quality_pass=False,
            empty_talk=True,
            logic_issue=True,
            source_used=False,
            answer_length=0,
            source_count=0,
            error=str(exc),
        )


def _rate(rows: list[QualityRow], key: str) -> float:
    if not rows:
        return 0.0
    return sum(1 for row in rows if bool(getattr(row, key))) / len(rows)


def _avg(rows: list[QualityRow], key: str) -> float:
    if not rows:
        return 0.0
    return sum(float(getattr(row, key)) for row in rows) / len(rows)


def _write_csv(rows: list[QualityRow], path: Path) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def _write_summary(rows: list[QualityRow], path: Path, label: str) -> None:
    summary = [
        ("样本数", f"{len(rows)}"),
        ("route_success_rate", f"{_rate(rows, 'route_ok'):.2%}"),
        ("structure_pass_rate", f"{sum(1 for r in rows if r.structure_score >= 18) / len(rows):.2%}"),
        ("evidence_coverage_rate", f"{_rate(rows, 'source_used'):.2%}"),
        ("text_quality_pass_rate", f"{_rate(rows, 'quality_pass'):.2%}"),
        ("empty_talk_rate", f"{_rate(rows, 'empty_talk'):.2%}"),
        ("logic_issue_rate", f"{_rate(rows, 'logic_issue'):.2%}"),
        ("avg_total_score", f"{_avg(rows, 'total_score'):.1f}"),
        ("avg_answer_length", f"{_avg(rows, 'answer_length'):.1f}"),
        ("avg_source_count", f"{_avg(rows, 'source_count'):.1f}"),
    ]
    lines = [
        f"# 文本质量基线评测结果（{label}）",
        "",
        "| 指标 | 数值 |",
        "|---|---:|",
        *[f"| {name} | {value} |" for name, value in summary],
        "",
        "## Case 明细",
        "",
        "| case_id | route | score | pass | empty_talk | logic_issue | source_count |",
        "|---|---|---:|---|---|---|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row.case_id} | {row.actual_route} | {row.total_score} | {row.quality_pass} | "
            f"{row.empty_talk} | {row.logic_issue} | {row.source_count} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate research-agent text quality.")
    parser.add_argument("--limit", type=int, default=0, help="Run only first N cases. 0 means all.")
    parser.add_argument("--offline", action="store_true", help="Disable API calls for a faster deterministic baseline.")
    parser.add_argument("--label", default="baseline", help="Label used in the markdown summary.")
    parser.add_argument("--mode", choices=["base", "base_rag", "full"], default="full", help="Ablation mode.")
    parser.add_argument("--out-csv", default=str(DETAIL_CSV), help="Output CSV path.")
    parser.add_argument("--out-md", default=str(SUMMARY_MD), help="Output markdown path.")
    args = parser.parse_args()

    load_dotenv(dotenv_path=ROOT / ".env")
    if args.offline:
        os.environ["OPENAI_API_KEY"] = ""
        os.environ["ZHIPUAI_API_KEY"] = ""
    if args.mode == "base":
        os.environ["RESEARCH_ENABLE_RAG"] = "0"
        os.environ["RESEARCH_ENABLE_SKILL"] = "0"
    elif args.mode == "base_rag":
        os.environ["RESEARCH_ENABLE_RAG"] = "1"
        os.environ["RESEARCH_ENABLE_SKILL"] = "0"
    else:
        os.environ["RESEARCH_ENABLE_RAG"] = "1"
        os.environ["RESEARCH_ENABLE_SKILL"] = "1"

    cases = list(csv.DictReader(TESTSET.open(encoding="utf-8-sig")))
    if args.limit > 0:
        cases = cases[: args.limit]
    rows = [_evaluate_case(row) for row in cases]
    if not rows:
        print("No cases to evaluate.")
        return 1

    out_csv = Path(args.out_csv)
    out_md = Path(args.out_md)
    _write_csv(rows, out_csv)
    _write_summary(rows, out_md, args.label)
    print(f"mode={args.mode}")
    print(f"wrote {out_csv}")
    print(f"wrote {out_md}")
    print(f"text_quality_pass_rate={_rate(rows, 'quality_pass'):.2%}")
    print(f"avg_total_score={_avg(rows, 'total_score'):.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
