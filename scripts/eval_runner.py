from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agent import run_financial_agent
TESTSET = ROOT / "eval" / "testset.csv"
FAILED_CASES = ROOT / "eval" / "failed_cases.csv"


@dataclass
class CaseResult:
    case_id: str
    bucket: str
    query: str
    expected_intent: str
    predicted_intent: str
    intent_ok: bool
    route_ok: bool
    compare_ok: bool
    text_ok: bool
    fail_reason: str


def _text_quality_ok(agent_result) -> bool:
    analysis = agent_result.analysis
    if analysis is None:
        return False
    summary = getattr(analysis, "plain_cashflow_summary", "") or ""
    outlook = getattr(analysis, "future_outlook", "") or ""
    risk = getattr(analysis, "risk_notes", "") or ""
    checks = [
        len(summary) >= 60,
        len(outlook) >= 70,
        all(k in summary for k in ["收入", "利润", "现金流"]),
        "不构成投资建议" in risk,
    ]
    return all(checks)


def _eval_one(row: dict[str, str]) -> CaseResult:
    q = row["query"]
    expected_intent = row["expected_intent"]
    bucket = row["bucket"]
    result = run_financial_agent(q)
    predicted = result.intent
    intent_ok = predicted == expected_intent

    if bucket == "compare":
        compare_ok = result.comparison is not None
        route_ok = compare_ok
    else:
        compare_ok = False
        route_ok = bool(result.snapshot.get("found")) and (result.analysis is not None)

    text_ok = _text_quality_ok(result) if route_ok else False

    reason = ""
    if not intent_ok:
        reason = f"intent_mismatch:{predicted}"
    elif not route_ok:
        reason = "route_failed"
    elif not text_ok:
        reason = "text_quality_failed"

    return CaseResult(
        case_id=row["id"],
        bucket=bucket,
        query=q,
        expected_intent=expected_intent,
        predicted_intent=predicted,
        intent_ok=intent_ok,
        route_ok=route_ok,
        compare_ok=compare_ok,
        text_ok=text_ok,
        fail_reason=reason,
    )


def _safe_div(a: int, b: int) -> float:
    return 0.0 if b == 0 else a / b


def main() -> None:
    rows = []
    with TESTSET.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    results = [_eval_one(r) for r in rows]
    total = len(results)
    intent_ok = sum(1 for r in results if r.intent_ok)
    route_ok = sum(1 for r in results if r.route_ok)
    text_ok = sum(1 for r in results if r.text_ok)
    failures = [r for r in results if r.fail_reason]

    compare_cases = [r for r in results if r.bucket == "compare"]
    compare_ok = sum(1 for r in compare_cases if r.compare_ok)

    print("=== Eval Baseline ===")
    print(f"total_cases: {total}")
    print(f"intent_accuracy: {_safe_div(intent_ok, total):.2%}")
    print(f"route_success_rate: {_safe_div(route_ok, total):.2%}")
    print(f"compare_success_rate: {_safe_div(compare_ok, len(compare_cases)):.2%}")
    print(f"text_quality_pass_rate: {_safe_div(text_ok, total):.2%}")
    print(f"empty_or_error_rate: {_safe_div(len([r for r in results if not r.route_ok]), total):.2%}")

    bucket_names = sorted(set(r.bucket for r in results))
    print("\n--- bucket breakdown ---")
    for b in bucket_names:
        subset = [r for r in results if r.bucket == b]
        b_total = len(subset)
        print(
            f"{b}: total={b_total}, intent={_safe_div(sum(x.intent_ok for x in subset), b_total):.2%}, "
            f"route={_safe_div(sum(x.route_ok for x in subset), b_total):.2%}, "
            f"text={_safe_div(sum(x.text_ok for x in subset), b_total):.2%}"
        )

    if failures:
        print("\n--- top failures ---")
        for r in failures[:10]:
            print(f"[{r.case_id}] {r.query} -> {r.fail_reason}")

    with FAILED_CASES.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["id", "bucket", "query", "expected_intent", "predicted_intent", "fail_reason"],
        )
        writer.writeheader()
        for r in failures:
            writer.writerow(
                {
                    "id": r.case_id,
                    "bucket": r.bucket,
                    "query": r.query,
                    "expected_intent": r.expected_intent,
                    "predicted_intent": r.predicted_intent,
                    "fail_reason": r.fail_reason,
                }
            )
    print(f"\nfailed_cases_saved: {FAILED_CASES}")


if __name__ == "__main__":
    main()
