from __future__ import annotations

from datetime import date, timedelta
from functools import lru_cache
import re
import time
from typing import Any

import pandas as pd

from src.net_utils import is_proxy_error, temporary_disable_proxy
from src.sample_data import SAMPLE_COMPANIES


GENERIC_OUTLOOK = "暂未接入该公司的管理层展望原文，当前先基于公开财务摘要做初步解读。"
GENERIC_CASHFLOW_SUMMARY = "现金流需要结合最新财务摘要判断，若公开接口缺字段则需要查看公司公告进一步确认。"


def _normalize_text(text: str) -> str:
    cleaned = re.sub(r"\s+", "", text or "")
    return cleaned.upper()


@lru_cache(maxsize=1)
def _load_a_share_universe() -> tuple[dict[str, str], ...]:
    try:
        import akshare as ak

        frame = ak.stock_info_a_code_name()
        if not isinstance(frame, pd.DataFrame) or frame.empty:
            return tuple()
        records: list[dict[str, str]] = []
        for _, row in frame.iterrows():
            code = str(row.get("code", "")).strip()
            name = str(row.get("name", "")).strip()
            if re.fullmatch(r"\d{6}", code) and name:
                records.append({"code": code, "name": name, "normalized_name": _normalize_text(name)})
        return tuple(records)
    except Exception:
        return tuple()


def _sample_match(normalized_query: str) -> dict[str, Any] | None:
    for name, item in SAMPLE_COMPANIES.items():
        for alias in item["aliases"]:
            if _normalize_text(alias) in normalized_query:
                return {
                    "found": True,
                    "company_name": name,
                    "stock_code": item["stock_code"],
                    "match_source": "sample_alias",
                    "candidates": [],
                }
    return None


def _universe_code_or_exact_match(normalized_query: str) -> dict[str, Any] | None:
    universe = _load_a_share_universe()
    if not universe:
        return None

    code_match = re.search(r"(?<!\d)\d{6}(?!\d)", normalized_query)
    if code_match:
        code = code_match.group(0)
        for item in universe:
            if item["code"] == code:
                return {
                    "found": True,
                    "company_name": item["name"],
                    "stock_code": item["code"],
                    "match_source": "akshare_code",
                    "candidates": [],
                }

    exact_name_matches = [item for item in universe if item["normalized_name"] and item["normalized_name"] in normalized_query]
    if exact_name_matches:
        best = sorted(exact_name_matches, key=lambda item: len(item["normalized_name"]), reverse=True)[0]
        return {
            "found": True,
            "company_name": best["name"],
            "stock_code": best["code"],
            "match_source": "akshare_name",
            "candidates": [],
        }

    return None


def _universe_fuzzy_match(normalized_query: str) -> dict[str, Any] | None:
    universe = _load_a_share_universe()
    if not universe:
        return None

    compact_query = re.sub(r"(帮我|看看|最近|怎么样|未来|赚钱|不赚钱|公司|股票|财报|分析|一下|如何|吗|呢|的|了)", "", normalized_query)
    if len(compact_query) >= 2:
        fuzzy = [item for item in universe if compact_query in item["normalized_name"]]
        if fuzzy:
            best = sorted(fuzzy, key=lambda item: len(item["normalized_name"]))[0]
            return {
                "found": True,
                "company_name": best["name"],
                "stock_code": best["code"],
                "match_source": "akshare_fuzzy",
                "candidates": fuzzy[:5],
            }

    return None


def identify_company(user_query: str) -> dict[str, Any]:
    normalized = _normalize_text(user_query)
    universe_exact = _universe_code_or_exact_match(normalized)
    if universe_exact:
        return universe_exact

    sample = _sample_match(normalized)
    if sample:
        return sample

    universe_fuzzy = _universe_fuzzy_match(normalized)
    if universe_fuzzy:
        return universe_fuzzy

    return {
        "found": False,
        "company_name": "",
        "stock_code": "",
        "match_source": "not_found",
        "candidates": [],
    }


def _report_columns(frame: pd.DataFrame) -> list[str]:
    columns = [str(col) for col in frame.columns]
    reports = [col for col in columns if re.fullmatch(r"\d{8}", col)]
    return sorted(reports, reverse=True)


def _find_indicator_row(frame: pd.DataFrame, keywords: list[str]) -> pd.Series | None:
    if frame.empty:
        return None
    text_frame = frame.astype(str)
    mask = pd.Series(False, index=frame.index)
    for keyword in keywords:
        mask = mask | text_frame.apply(lambda col: col.str.contains(keyword, na=False, regex=False)).any(axis=1)
    matched = frame[mask]
    if matched.empty:
        return None
    return matched.iloc[0]


def _latest_value(frame: pd.DataFrame, keywords: list[str]) -> tuple[str | None, str | None]:
    row = _find_indicator_row(frame, keywords)
    if row is None:
        return None, None
    for report in _report_columns(frame):
        value = row.get(report)
        if pd.notna(value) and str(value).strip().lower() not in {"", "nan", "none", "--"}:
            return str(value), report
    return None, None


def _format_yuan_to_yi(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        amount = float(str(value).replace(",", ""))
    except ValueError:
        return value
    return f"约 {amount / 100000000:.2f} 亿元"


def _format_percent(value: str | None) -> str | None:
    if value is None:
        return None
    raw = str(value).strip()
    try:
        number = float(raw.replace("%", "").replace(",", ""))
    except ValueError:
        return raw
    if abs(number) <= 1:
        number *= 100
    return f"{number:.2f}%"


def _fetch_akshare_metrics(stock_code: str) -> dict[str, Any]:
    import akshare as ak

    metrics: dict[str, Any] = {}
    abstract = ak.stock_financial_abstract(symbol=stock_code)
    if not isinstance(abstract, pd.DataFrame) or abstract.empty:
        return metrics

    revenue, revenue_period = _latest_value(abstract, ["营业总收入", "营业收入"])
    net_profit, profit_period = _latest_value(abstract, ["归母净利润", "净利润"])
    cash_flow, cash_period = _latest_value(abstract, ["经营活动产生的现金流量净额", "经营现金流量净额"])
    revenue_yoy, _ = _latest_value(abstract, ["营业总收入同比增长率", "营业收入同比增长率"])
    profit_yoy, _ = _latest_value(abstract, ["净利润同比增长率", "归母净利润同比增长率"])

    metrics["revenue"] = _format_yuan_to_yi(revenue)
    metrics["net_profit"] = _format_yuan_to_yi(net_profit)
    metrics["operating_cash_flow"] = _format_yuan_to_yi(cash_flow)
    metrics["revenue_yoy"] = _format_percent(revenue_yoy)
    metrics["net_profit_yoy"] = _format_percent(profit_yoy)
    metrics["report_period"] = revenue_period or profit_period or cash_period
    metrics["akshare_shape"] = f"{abstract.shape[0]}行 x {abstract.shape[1]}列"
    return {key: value for key, value in metrics.items() if value}


def _fetch_akshare_metrics_with_retry(stock_code: str) -> dict[str, Any]:
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            return _fetch_akshare_metrics(stock_code)
        except Exception as exc:
            last_exc = exc
            if is_proxy_error(exc):
                with temporary_disable_proxy():
                    try:
                        return _fetch_akshare_metrics(stock_code)
                    except Exception as inner_exc:
                        last_exc = inner_exc
            if not _is_transient_akshare_error(last_exc):
                raise
            if attempt < 2:
                time.sleep(0.8 * (2**attempt))
    raise RuntimeError(f"AKShare metrics retry exhausted: {last_exc}")


@lru_cache(maxsize=256)
def _fetch_akshare_daily_prices(stock_code: str) -> tuple[dict[str, Any], ...]:
    import akshare as ak

    end = date.today()
    start = end - timedelta(days=140)
    start_text = start.strftime("%Y%m%d")
    end_text = end.strftime("%Y%m%d")
    market_prefix = "sh" if stock_code.startswith(("5", "6", "9")) else "sz"

    frame = pd.DataFrame()
    errors: list[str] = []
    fetchers = (
        lambda: ak.stock_zh_a_hist_tx(
            symbol=f"{market_prefix}{stock_code}",
            start_date=start_text,
            end_date=end_text,
            adjust="qfq",
            timeout=10,
        ),
        lambda: ak.stock_zh_a_daily(
            symbol=f"{market_prefix}{stock_code}",
            start_date=start_text,
            end_date=end_text,
            adjust="qfq",
        ),
        lambda: ak.stock_zh_a_hist(
            symbol=stock_code,
            period="daily",
            start_date=start_text,
            end_date=end_text,
            adjust="qfq",
        ),
    )
    for fetch in fetchers:
        try:
            candidate = fetch()
            if isinstance(candidate, pd.DataFrame) and not candidate.empty:
                frame = candidate
                break
        except Exception as exc:
            errors.append(str(exc))

    if not isinstance(frame, pd.DataFrame) or frame.empty:
        if errors:
            raise RuntimeError("；".join(errors[-2:]))
        return tuple()

    normalized = frame.rename(
        columns={
            "日期": "date",
            "开盘": "open",
            "收盘": "close",
            "最高": "high",
            "最低": "low",
            "成交量": "volume",
            "成交额": "turnover",
            "amount": "turnover",
            "涨跌幅": "pct_change",
        }
    )
    required = ["date", "open", "close", "high", "low"]
    if any(column not in normalized.columns for column in required):
        return tuple()

    normalized["date"] = normalized["date"].astype(str)
    for column in ["open", "close", "high", "low", "volume", "turnover", "pct_change"]:
        if column in normalized.columns:
            normalized[column] = pd.to_numeric(normalized[column], errors="coerce")

    records = normalized[
        [column for column in ["date", "open", "close", "high", "low", "volume", "turnover", "pct_change"] if column in normalized.columns]
    ].dropna(subset=["date", "close"])
    records = records.where(pd.notnull(records), None)
    return tuple(records.to_dict(orient="records"))


def _fetch_akshare_daily_prices_with_retry(stock_code: str) -> tuple[dict[str, Any], ...]:
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            return _fetch_akshare_daily_prices(stock_code)
        except Exception as exc:
            last_exc = exc
            if is_proxy_error(exc):
                with temporary_disable_proxy():
                    try:
                        return _fetch_akshare_daily_prices(stock_code)
                    except Exception as inner_exc:
                        last_exc = inner_exc
            if not _is_transient_akshare_error(last_exc):
                raise
            if attempt < 2:
                time.sleep(0.8 * (2**attempt))
    raise RuntimeError(f"AKShare daily retry exhausted: {last_exc}")


def _is_transient_akshare_error(exc: Exception) -> bool:
    text = str(exc).lower()
    retry_signals = (
        "timeout",
        "timed out",
        "temporarily unavailable",
        "connection aborted",
        "connection reset",
        "max retries exceeded",
        "503",
        "502",
        "504",
        "rate limit",
        "too many requests",
    )
    return any(signal in text for signal in retry_signals)


def build_company_snapshot(user_query: str) -> dict[str, Any]:
    resolved = identify_company(user_query)
    if not resolved["found"]:
        return {
            "found": False,
            "company_name": "",
            "stock_code": "",
            "match_source": resolved["match_source"],
            "data_source": "not_found",
            "data_warning": "暂未识别到 A 股公司。请尝试输入完整公司简称或 6 位股票代码。",
            "data_quality": {
                "live_metric_count": 0,
                "fallback_enabled": True,
                "report_period": "not_found",
            },
            "financial_metrics": {},
            "cash_flow_summary": "",
            "management_outlook": "",
            "daily_prices": [],
            "price_warning": "",
            "candidates": resolved["candidates"],
        }

    company_name = resolved["company_name"]
    stock_code = resolved["stock_code"]
    sample = SAMPLE_COMPANIES.get(company_name)

    financial_metrics = dict(sample["financial_metrics"]) if sample else {}
    cash_flow_summary = sample["cash_flow_summary"] if sample else GENERIC_CASHFLOW_SUMMARY
    management_outlook = sample["management_outlook"] if sample else GENERIC_OUTLOOK
    data_source = "sample" if sample else "akshare_lookup"
    data_warning = ""
    live_metrics: dict[str, Any] = {}
    daily_prices: tuple[dict[str, Any], ...] = tuple()
    price_warning = ""

    try:
        live_metrics = _fetch_akshare_metrics_with_retry(stock_code)
        if live_metrics:
            financial_metrics.update(live_metrics)
            data_source = "akshare+sample" if sample else "akshare"
        elif not sample:
            data_warning = "已识别公司，但公开财务摘要暂未返回可用指标。"
    except Exception as exc:
        data_warning = f"AKShare 数据获取失败，已使用可用兜底数据：{exc}"

    try:
        daily_prices = _fetch_akshare_daily_prices_with_retry(stock_code)
        if not daily_prices:
            price_warning = "暂未获取到近期日线行情。"
    except Exception as exc:
        price_warning = f"近期日线行情获取失败，已暂不展示走势图。原因：{str(exc).splitlines()[0][:80]}"

    return {
        "found": True,
        "company_name": company_name,
        "stock_code": stock_code,
        "match_source": resolved["match_source"],
        "data_source": data_source,
        "data_warning": data_warning,
        "data_quality": {
            "live_metric_count": len(live_metrics),
            "fallback_enabled": True,
            "report_period": financial_metrics.get("report_period", "sample" if sample else "unknown"),
        },
        "financial_metrics": financial_metrics,
        "cash_flow_summary": cash_flow_summary,
        "management_outlook": management_outlook,
        "daily_prices": list(daily_prices),
        "price_warning": price_warning,
        "candidates": resolved["candidates"],
    }
