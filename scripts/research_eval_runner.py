from __future__ import annotations

import csv
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

from src.research_agent import run_company_research_agent


TESTSET = ROOT / "eval" / "research_testset.csv"


def _has_structure(result) -> bool:
    required = [
        result.one_line_conclusion,
        result.business_overview,
        result.operating_performance,
        result.profitability_quality,
        result.cashflow_quality,
        result.growth_and_industry,
        result.major_risks,
    ]
    return all(bool(str(item).strip()) for item in required) and len(result.tracking_checklist) >= 3


def _has_evidence(result) -> bool:
    return bool(result.source_notes) and any(note.source_type for note in result.source_notes)


def _text_quality_ok(result) -> bool:
    text = " ".join(
        [
            result.one_line_conclusion,
            result.business_overview,
            result.operating_performance,
            result.profitability_quality,
            result.cashflow_quality,
            result.growth_and_industry,
            result.major_risks,
        ]
    )
    forbidden = ["买入", "卖出", "满仓", "清仓", "梭哈", "目标价"]
    return len(text) >= 120 and not any(word in text for word in forbidden)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run research eval cases.")
    parser.add_argument("--limit", type=int, default=0, help="Run only first N cases, 0 means all.")
    args = parser.parse_args()
    load_dotenv(dotenv_path=ROOT / ".env")
    rows = list(csv.DictReader(TESTSET.open(encoding="utf-8-sig")))
    if args.limit and args.limit > 0:
        rows = rows[: args.limit]
    if not rows:
        print("No research eval cases found.")
        return 1

    results = []
    for row in rows:
        case_id = row["case_id"]
        query = row["query"]
        expected_route = row["expected_route"]
        try:
            result = run_company_research_agent(query)
            route_ok = result.report_type == expected_route
            structure_ok = _has_structure(result)
            evidence_ok = _has_evidence(result)
            quality_ok = _text_quality_ok(result)
            results.append(
                {
                    "case_id": case_id,
                    "query": query,
                    "expected_route": expected_route,
                    "actual_route": result.report_type,
                    "route_ok": route_ok,
                    "structure_ok": structure_ok,
                    "evidence_ok": evidence_ok,
                    "quality_ok": quality_ok,
                }
            )
        except Exception as exc:
            results.append(
                {
                    "case_id": case_id,
                    "query": query,
                    "expected_route": expected_route,
                    "actual_route": "error",
                    "route_ok": False,
                    "structure_ok": False,
                    "evidence_ok": False,
                    "quality_ok": False,
                    "error": str(exc),
                }
            )

    total = len(results)
    route_rate = sum(item["route_ok"] for item in results) / total
    structure_rate = sum(item["structure_ok"] for item in results) / total
    evidence_rate = sum(item["evidence_ok"] for item in results) / total
    quality_rate = sum(item["quality_ok"] for item in results) / total

    print(f"route_success_rate={route_rate:.2%}")
    print(f"research_structure_pass_rate={structure_rate:.2%}")
    print(f"evidence_coverage_rate={evidence_rate:.2%}")
    print(f"text_quality_pass_rate={quality_rate:.2%}")

    failed = [item for item in results if not all([item["route_ok"], item["structure_ok"], item["evidence_ok"], item["quality_ok"]])]
    if failed:
        print("failed_cases:")
        for item in failed:
            print(
                f"- {item['case_id']} expected={item['expected_route']} actual={item['actual_route']} "
                f"route={item['route_ok']} structure={item['structure_ok']} evidence={item['evidence_ok']} quality={item['quality_ok']}"
            )
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())
