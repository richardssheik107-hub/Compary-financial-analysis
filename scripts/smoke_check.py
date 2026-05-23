from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402
from src.agent import run_financial_agent  # noqa: E402


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str


def check_health(port: int) -> CheckResult:
    url = f"http://localhost:{port}/_stcore/health"
    try:
        with urllib.request.urlopen(url, timeout=6) as response:
            body = response.read().decode("utf-8", errors="ignore").strip()
        ok = body.lower() == "ok"
        return CheckResult("streamlit_health", ok, f"url={url} body={body!r}")
    except urllib.error.URLError as exc:
        return CheckResult("streamlit_health", False, f"url={url} error={exc}")


def check_single_company() -> CheckResult:
    result = run_financial_agent("贵州茅台")
    ok = bool(result.snapshot.get("found")) and result.analysis is not None and len(result.steps) >= 3
    detail = (
        f"found={result.snapshot.get('found')} steps={len(result.steps)} "
        f"ai_status={(result.analysis.ai_status if result.analysis else 'none')}"
    )
    return CheckResult("single_company_flow", ok, detail)


def check_compare_flow() -> CheckResult:
    result = run_financial_agent("宁德时代和比亚迪谁更好")
    comparison = result.comparison or {}
    ok = (
        result.intent == "财报对比"
        and bool(comparison)
        and len(comparison.get("rows", [])) >= 4
        and len(comparison.get("followups", [])) >= 1
    )
    detail = (
        f"intent={result.intent} comparison={bool(comparison)} "
        f"rows={len(comparison.get('rows', []))} followups={len(comparison.get('followups', []))}"
    )
    return CheckResult("compare_flow", ok, detail)


def check_compare_fail_hint() -> CheckResult:
    result = run_financial_agent("A和B谁更好")
    warning = result.warnings[0] if result.warnings else ""
    hint_tokens = ("两个", "公司", "补充", "公司名", "代码")
    is_general_route = result.intent in {"通用问答", "通用财报问答", "财报解读"}
    ok = is_general_route and any(token in warning for token in hint_tokens)
    detail = f"intent={result.intent} found={result.snapshot.get('found')} warning={warning}"
    return CheckResult("compare_fail_hint", ok, detail)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run smoke checks for financial agent workflows.")
    parser.add_argument("--port", type=int, default=8502, help="Expected Streamlit port for health check.")
    parser.add_argument("--skip-health", action="store_true", help="Skip HTTP health endpoint check.")
    args = parser.parse_args()

    load_dotenv()

    checks: list[CheckResult] = []
    if not args.skip_health:
        checks.append(check_health(args.port))
    checks.extend([check_single_company(), check_compare_flow(), check_compare_fail_hint()])

    passed = [item for item in checks if item.passed]
    failed = [item for item in checks if not item.passed]
    summary = {
        "total": len(checks),
        "passed": len(passed),
        "failed": len(failed),
        "results": [asdict(item) for item in checks],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
