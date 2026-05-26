from __future__ import annotations

from dataclasses import asdict
from datetime import date
from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

from src.agent import run_financial_agent
from src.context_store import ConversationContext, context_from_state
from src.data_service import build_company_snapshot
from src.models import AnalysisResult
from src.research_agent import run_company_research_agent
from src.research_models import ResearchResult

load_dotenv()


def _build_research_markdown(result: ResearchResult) -> str:
    source_lines = []
    for note in result.source_notes:
        source_lines.append(f"- {note.source_type} | {note.title} | {note.detail}")
    if not source_lines:
        source_lines.append("- 暂无来源记录")

    tracking_lines = [f"- {item}" for item in result.tracking_checklist] or ["- 暂无后续跟踪项"]
    limitation_lines = [f"- {item}" for item in result.limitations] or ["- 暂无额外限制说明"]
    evidence_lines = [f"- {k}: {' / '.join(v)}" for k, v in (result.evidence_by_section or {}).items()] or ["- 暂无证据绑定"]

    return "\n".join(
        [
            f"# {result.title}",
            "",
            "## 一句话结论",
            result.one_line_conclusion,
            "",
            "## 公司是做什么的",
            result.business_overview,
            "",
            "## 近年经营表现",
            result.operating_performance,
            "",
            "## 盈利质量",
            result.profitability_quality,
            "",
            "## 现金流质量",
            result.cashflow_quality,
            "",
            "## 成长性与行业位置",
            result.growth_and_industry,
            "",
            "## 主要风险",
            result.major_risks,
            "",
            f"## 可信度\n{result.confidence_score}/100",
            "",
            "## 资料命中概览",
            f"- reports: {int(result.source_summary.get('reports', 0))}",
            f"- company_info: {int(result.source_summary.get('company_info', 0))}",
            f"- industry_info: {int(result.source_summary.get('industry_info', 0))}",
            f"- total: {int(result.source_summary.get('total', 0))}",
            f"- scanned_files: {int(result.source_summary.get('scanned_files', 0))}",
            f"- matched_files: {int(result.source_summary.get('matched_files', 0))}",
            f"- pdf_scanned: {int(result.source_summary.get('pdf_scanned', 0))}",
            f"- pdf_empty: {int(result.source_summary.get('pdf_empty', 0))}",
            f"- matched_titles: {', '.join(result.source_summary.get('matched_titles', [])) or '无'}",
            "",
            "## 后续跟踪清单",
            *tracking_lines,
            "",
            "## 依据来源",
            *source_lines,
            "",
            "## 证据绑定",
            *evidence_lines,
            "",
            "## 限制说明",
            *limitation_lines,
            "",
            "> 免责声明：本内容仅用于公开信息解读与学习参考，不构成投资建议。",
        ]
    )


def apply_styles() -> None:
    st.markdown(
        """
        <style>
        #MainMenu, footer, header { visibility: hidden; height: 0; }
        html, body, [data-testid="stAppViewContainer"], .stApp {
            background: radial-gradient(circle at 78% 16%, #2f4524 0%, #173f30 32%, #0f2f24 64%, #0a221a 100%);
            color: #F3EFD7;
        }
        .block-container { max-width: 1180px; padding-top: 2rem; padding-bottom: 2.5rem; }
        .hero { text-align: center; margin: 0.2rem auto 1.2rem; }
        .hero h1 { color: #F6F2DD; font-size: 2.1rem; font-weight: 760; margin: 0 0 0.45rem; letter-spacing: 0; }
        .hero p { color: #ECE5C5; font-size: 0.98rem; line-height: 1.8; margin: 0; }
        .custom-card {
            background: rgba(20, 39, 31, 0.72); border: 1px solid rgba(201, 182, 120, 0.42);
            border-radius: 12px; padding: 16px 18px; margin-bottom: 0.9rem;
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.22);
        }
        .card-title { color: #F7F2DD; font-size: 1rem; font-weight: 730; margin: 0 0 0.5rem; }
        .card-body { color: #F1EBD2; font-size: 0.96rem; line-height: 1.8; margin: 0; }
        .section-title { color: #F7F2DD; font-size: 1.05rem; font-weight: 730; margin: 0.2rem 0 0.7rem; }
        .context-main { color: #F7F2DD; font-weight: 700; font-size: 1.55rem; }
        .risk-note { background: rgba(85, 70, 25, 0.22); border: 1px solid rgba(214, 190, 123, 0.58); color: #F3E9C2; border-radius: 12px; padding: 0.9rem 1rem; line-height: 1.75; font-weight: 620; }
        div[data-testid="stForm"] {
            background: rgba(17, 36, 29, 0.78); border: 1px solid rgba(201, 182, 120, 0.42);
            border-radius: 12px; padding: 18px; box-shadow: 0 8px 20px rgba(0, 0, 0, 0.24);
        }
        div[data-testid="stButton"] button, div[data-testid="stFormSubmitButton"] button {
            border-radius: 12px; min-height: 3rem; font-weight: 720; border: 0;
            background: linear-gradient(135deg, #2D8CF0 0%, #1677FF 100%); color: #F8F4E2;
            box-shadow: 0 6px 14px rgba(45, 140, 240, 0.28);
        }
        div[data-testid="stDownloadButton"] button {
            border-radius: 12px; min-height: 3rem; font-weight: 720; border: 0;
            background: linear-gradient(135deg, #1D9D5B 0%, #147E48 100%);
            color: #F8F4E2;
            box-shadow: 0 6px 14px rgba(20, 126, 72, 0.32);
        }
        div[data-testid="stDataFrame"], div[data-testid="stPlotlyChart"], div[data-testid="stExpander"] {
            border: 1px solid rgba(201, 182, 120, 0.36); border-radius: 12px; overflow: hidden; box-shadow: 0 8px 20px rgba(0, 0, 0, 0.20);
        }
        label, p, span, li, small, h1, h2, h3, h4, h5, h6 { color: #F3EFD7 !important; }
        div[data-testid="stTextInput"] label,
        div[data-testid="stTextArea"] label,
        div[data-testid="stSelectbox"] label { color: #F3EFD7 !important; font-weight: 650; }
        div[data-testid="stTextInput"] input,
        div[data-testid="stTextArea"] textarea {
            color: #F7F2DD !important;
            background: rgba(11, 27, 22, 0.90) !important;
            border: 1px solid rgba(202, 184, 124, 0.45) !important;
        }
        div[data-testid="stTextInput"] input::placeholder,
        div[data-testid="stTextArea"] textarea::placeholder { color: #DDD4B0 !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _score_to_100(value: float) -> int:
    return max(0, min(100, round(value * 10)))


def _init_state() -> None:
    st.session_state.setdefault("conversation_context", ConversationContext().to_dict())
    st.session_state.setdefault("last_steps", [])
    st.session_state.setdefault("last_suggested_questions", [])


def _build_radar_chart(result: AnalysisResult) -> go.Figure:
    labels = ["盈利能力", "存钱能力", "未来潜力"]
    values = [_score_to_100(result.scores.profitability), _score_to_100(result.scores.cash_saving), _score_to_100(result.scores.future_potential)]
    fig = go.Figure(data=[go.Scatterpolar(r=values + [values[0]], theta=labels + [labels[0]], fill="toself", line=dict(color="#2D8CF0", width=3), fillcolor="rgba(45,140,240,0.20)")])
    fig.update_layout(height=320, margin=dict(l=20, r=20, t=20, b=20), showlegend=False)
    return fig


def _build_price_chart(snapshot: dict) -> go.Figure:
    prices = pd.DataFrame(snapshot.get("daily_prices") or [])
    fig = go.Figure()
    if prices.empty:
        return fig
    prices["date"] = pd.to_datetime(prices["date"], errors="coerce")
    prices = prices.dropna(subset=["date", "open", "high", "low", "close"]).sort_values("date")
    for window in [5, 10, 20]:
        prices[f"ma{window}"] = prices["close"].rolling(window=window, min_periods=window).mean()
    display = prices[(prices["date"] >= pd.Timestamp(date.today()) - pd.Timedelta(days=90)) & (prices["date"] <= pd.Timestamp(date.today()))].copy()
    if display.empty:
        display = prices.tail(60).copy()
    display["date_label"] = display["date"].dt.strftime("%Y-%m-%d")
    fig.add_trace(
        go.Candlestick(
            x=display["date_label"],
            open=display["open"],
            high=display["high"],
            low=display["low"],
            close=display["close"],
            increasing_line_color="#E84A5F",
            decreasing_line_color="#13A579",
            increasing_fillcolor="rgba(232, 74, 95, 0.50)",
            decreasing_fillcolor="rgba(19, 165, 121, 0.50)",
            whiskerwidth=0.4,
            name="日线",
        )
    )
    for window, (name, color, width) in {5: ("MA5", "#F59E0B", 2.0), 10: ("MA10", "#2D8CF0", 2.0), 20: ("MA20", "#8B5CF6", 2.0)}.items():
        fig.add_trace(go.Scatter(x=display["date_label"], y=display[f"ma{window}"], mode="lines", line=dict(color=color, width=width), name=name, connectgaps=False))
    fig.update_layout(
        height=360,
        margin=dict(l=12, r=12, t=34, b=8),
        xaxis=dict(showgrid=False, rangeslider=dict(visible=False), type="category", nticks=8),
        yaxis=dict(title=dict(text="价格"), gridcolor="#D8CFAE"),
        legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="left", x=0),
        hovermode="x unified",
        showlegend=True,
        paper_bgcolor="#F4EED8",
        plot_bgcolor="#F4EED8",
    )
    return fig


def _render_context_bar() -> None:
    context = context_from_state(st.session_state.get("conversation_context"))
    company = context.company_name or "无"
    compare_pair = " vs ".join(context.compare_pair) if context.compare_pair else "无"
    c1, c2 = st.columns([0.78, 0.22])
    with c1:
        st.markdown(f'<div class="custom-card"><div class="context-main">当前上下文公司：{escape(company)}</div><div class="context-main" style="margin-top:0.35rem;">最近对比对：{escape(compare_pair)}</div></div>', unsafe_allow_html=True)
    with c2:
        if st.button("清空上下文", use_container_width=True):
            st.session_state["conversation_context"] = ConversationContext().to_dict()
            st.session_state["last_steps"] = []
            st.session_state["last_suggested_questions"] = []
            st.rerun()


def _render_agent_steps() -> None:
    steps = st.session_state.get("last_steps") or []
    if not steps:
        return
    st.markdown('<p class="section-title">代理执行流程</p>', unsafe_allow_html=True)
    for i, step in enumerate(steps, start=1):
        status = "成功" if step.get("status") == "success" else "失败"
        summary = str(step.get("summary") or "")
        st.markdown(f'<div class="custom-card"><p class="card-title">步骤{i}：{escape(str(step.get("step_name") or ""))}</p><p class="card-body">状态：{status}</p><p class="card-body">{escape(summary)}</p></div>', unsafe_allow_html=True)


def _render_suggested_questions() -> None:
    questions = st.session_state.get("last_suggested_questions") or []
    if not questions:
        return
    st.markdown('<p class="section-title">延申问题建议</p>', unsafe_allow_html=True)
    for q in questions[:3]:
        st.markdown(f'<div class="custom-card"><p class="card-body">{escape(str(q))}</p></div>', unsafe_allow_html=True)


def _render_metrics_table(snapshot: dict) -> None:
    metrics = snapshot.get("financial_metrics", {})
    rows = [("报告期", metrics.get("report_period")), ("营业收入", metrics.get("revenue")), ("净利润", metrics.get("net_profit")), ("经营现金流", metrics.get("operating_cash_flow")), ("营收同比", metrics.get("revenue_yoy")), ("净利润同比", metrics.get("net_profit_yoy"))]
    st.dataframe(pd.DataFrame(rows, columns=["指标", "数值"]).fillna("暂无"), use_container_width=True, hide_index=True)


def _render_research_report(result: ResearchResult) -> None:
    # 用户态简洁展示：隐藏资料命中概览/证据细节，统一在结尾展示参考来源与后台数据
    st.markdown('<p class="section-title">深度研究报告</p>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="custom-card"><p class="card-title">{escape(result.title)}</p>'
        f'<p class="card-body"><strong>一句话结论：</strong>{escape(result.one_line_conclusion)}</p>'
        f'<p class="card-body"><strong>业务概览：</strong>{escape(result.business_overview)}</p>'
        f'<p class="card-body"><strong>经营表现：</strong>{escape(result.operating_performance)}</p>'
        f'<p class="card-body"><strong>盈利质量：</strong>{escape(result.profitability_quality)}</p>'
        f'<p class="card-body"><strong>现金流质量：</strong>{escape(result.cashflow_quality)}</p>'
        f'<p class="card-body"><strong>成长与行业：</strong>{escape(result.growth_and_industry)}</p>'
        f'<p class="card-body"><strong>主要风险：</strong>{escape(result.major_risks)}</p>'
        f'<p class="card-body"><strong>可信度：</strong>{result.confidence_score}/100</p></div>',
        unsafe_allow_html=True,
    )
    if result.tracking_checklist:
        checklist = "".join(f"<li>{escape(item)}</li>" for item in result.tracking_checklist)
        st.markdown(
            f'<div class="custom-card"><p class="card-title">后续跟踪清单</p><ul class="card-body">{checklist}</ul></div>',
            unsafe_allow_html=True,
        )
    _render_research_charts(result)
    with st.expander("参考来源", expanded=False):
        summary_rows = [
            {"字段": "reports", "值": int(result.source_summary.get("reports", 0))},
            {"字段": "company_info", "值": int(result.source_summary.get("company_info", 0))},
            {"字段": "industry_info", "值": int(result.source_summary.get("industry_info", 0))},
            {"字段": "total", "值": int(result.source_summary.get("total", 0))},
            {"字段": "scanned_files", "值": int(result.source_summary.get("scanned_files", 0))},
            {"字段": "matched_files", "值": int(result.source_summary.get("matched_files", 0))},
            {"字段": "pdf_scanned", "值": int(result.source_summary.get("pdf_scanned", 0))},
            {"字段": "pdf_empty", "值": int(result.source_summary.get("pdf_empty", 0))},
            {"字段": "confidence_score", "值": int(result.confidence_score)},
        ]
        st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)
        if result.source_notes:
            rows = [{"source_type": note.source_type, "title": note.title, "detail": note.detail} for note in result.source_notes]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        if result.evidence_by_section:
            ev_rows = [{"section": k, "evidence_types": " / ".join(v)} for k, v in result.evidence_by_section.items()]
            st.dataframe(pd.DataFrame(ev_rows), use_container_width=True, hide_index=True)
        matched_titles = [str(x) for x in (result.source_summary.get("matched_titles") or []) if str(x).strip()]
        if matched_titles:
            st.markdown(
                '<div class="custom-card"><p class="card-body">' + "；".join(escape(x) for x in matched_titles) + "</p></div>",
                unsafe_allow_html=True,
            )
    if result.limitations:
        st.info("；".join(result.limitations))
    st.download_button(
        "导出研究报告（Markdown）",
        data=_build_research_markdown(result),
        file_name="company_research_report.md",
        mime="text/markdown",
        use_container_width=True,
    )
    return
    st.markdown('<p class="section-title">深度研究报告</p>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="custom-card"><p class="card-title">{escape(result.title)}</p>'
        f'<p class="card-body"><strong>一句话结论：</strong>{escape(result.one_line_conclusion)}</p>'
        f'<p class="card-body"><strong>业务概览：</strong>{escape(result.business_overview)}</p>'
        f'<p class="card-body"><strong>经营表现：</strong>{escape(result.operating_performance)}</p>'
        f'<p class="card-body"><strong>盈利质量：</strong>{escape(result.profitability_quality)}</p>'
        f'<p class="card-body"><strong>现金流质量：</strong>{escape(result.cashflow_quality)}</p>'
        f'<p class="card-body"><strong>成长与行业：</strong>{escape(result.growth_and_industry)}</p>'
        f'<p class="card-body"><strong>主要风险：</strong>{escape(result.major_risks)}</p>'
        f'<p class="card-body"><strong>可信度：</strong>{result.confidence_score}/100</p></div>',
        unsafe_allow_html=True,
    )
    if result.tracking_checklist:
        checklist = "".join(f"<li>{escape(item)}</li>" for item in result.tracking_checklist)
        st.markdown(f'<div class="custom-card"><p class="card-title">后续跟踪清单</p><ul class="card-body">{checklist}</ul></div>', unsafe_allow_html=True)
    if result.source_notes:
        rows = [{"来源类型": note.source_type, "标题": note.title, "说明": note.detail} for note in result.source_notes]
        st.markdown('<p class="section-title">依据来源</p>', unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    if result.evidence_by_section:
        ev_rows = [{"报告段落": k, "证据类型": " / ".join(v)} for k, v in result.evidence_by_section.items()]
        st.markdown('<p class="section-title">证据绑定</p>', unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(ev_rows), use_container_width=True, hide_index=True)
    _render_research_charts(result)
    summary_rows = [
        {"资料类型": "reports", "命中数量": int(result.source_summary.get("reports", 0))},
        {"资料类型": "company_info", "命中数量": int(result.source_summary.get("company_info", 0))},
        {"资料类型": "industry_info", "命中数量": int(result.source_summary.get("industry_info", 0))},
        {"资料类型": "total", "命中数量": int(result.source_summary.get("total", 0))},
        {"资料类型": "scanned_files", "命中数量": int(result.source_summary.get("scanned_files", 0))},
        {"资料类型": "matched_files", "命中数量": int(result.source_summary.get("matched_files", 0))},
        {"资料类型": "pdf_scanned", "命中数量": int(result.source_summary.get("pdf_scanned", 0))},
        {"资料类型": "pdf_empty", "命中数量": int(result.source_summary.get("pdf_empty", 0))},
    ]
    st.markdown('<p class="section-title">资料命中概览</p>', unsafe_allow_html=True)
    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)
    matched_titles = [str(x) for x in (result.source_summary.get("matched_titles") or []) if str(x).strip()]
    if matched_titles:
        st.markdown('<p class="section-title">命中资料明细</p>', unsafe_allow_html=True)
        st.markdown(
            '<div class="custom-card"><p class="card-body">' + "；".join(escape(x) for x in matched_titles) + "</p></div>",
            unsafe_allow_html=True,
        )
    if int(result.source_summary.get("pdf_scanned", 0)) > 0 and int(result.source_summary.get("pdf_empty", 0)) > 0:
        st.warning("检测到部分 PDF 无法提取文本（常见于扫描版 PDF），建议补充 txt/md 摘要或可复制文本版 PDF。")
    if result.limitations:
        st.info("；".join(result.limitations))
    st.download_button(
        "导出研究报告（Markdown）",
        data=_build_research_markdown(result),
        file_name="company_research_report.md",
        mime="text/markdown",
        use_container_width=True,
    )


def _render_research_charts(result: ResearchResult) -> None:
    if result.key_metrics:
        company = str(result.key_metrics.get("company") or "目标公司")
        labels = ["营业收入(亿元)", "净利润(亿元)", "经营现金流(亿元)"]
        values = [
            result.key_metrics.get("revenue"),
            result.key_metrics.get("net_profit"),
            result.key_metrics.get("operating_cash_flow"),
        ]
        points = [(l, float(v)) for l, v in zip(labels, values) if isinstance(v, (int, float))]
        if points:
            st.markdown('<p class="section-title">研究图表：经营质量三指标</p>', unsafe_allow_html=True)
            fig = go.Figure(
                data=[
                    go.Bar(
                        x=[p[0] for p in points],
                        y=[p[1] for p in points],
                        marker_color=["#2D8CF0", "#13A579", "#F59E0B"][: len(points)],
                        name=company,
                    )
                ]
            )
            fig.update_layout(height=320, margin=dict(l=20, r=20, t=20, b=20), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    if result.compare_metrics:
        rows = [row for row in result.compare_metrics if isinstance(row.get("a"), (int, float)) and isinstance(row.get("b"), (int, float))]
        if rows:
            st.markdown('<p class="section-title">研究图表：双公司核心指标对比</p>', unsafe_allow_html=True)
            company_a = str(rows[0].get("company_a") or "公司A")
            company_b = str(rows[0].get("company_b") or "公司B")
            fig = go.Figure()
            fig.add_trace(go.Bar(name=company_a, x=[r["label"] for r in rows], y=[r["a"] for r in rows], marker_color="#2D8CF0"))
            fig.add_trace(go.Bar(name=company_b, x=[r["label"] for r in rows], y=[r["b"] for r in rows], marker_color="#13A579"))
            fig.update_layout(height=340, barmode="group", margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)


def _render_analysis(snapshot: dict, result: AnalysisResult) -> None:
    st.success(f"公司：{snapshot.get('company_name')}（{snapshot.get('stock_code')}）")
    if snapshot.get("data_warning"):
        st.warning(_friendly_data_warning(str(snapshot.get("data_warning"))))
    if snapshot.get("price_warning"):
        st.warning(_friendly_data_warning(str(snapshot.get("price_warning"))))
    left, right = st.columns([7, 3], gap="large")
    with left:
        st.markdown('<p class="section-title">白话解读</p>', unsafe_allow_html=True)
        st.markdown(f'<div class="custom-card"><p class="card-body">{escape(result.plain_cashflow_summary)}</p></div>', unsafe_allow_html=True)
        st.markdown('<p class="section-title">未来一年怎么看</p>', unsafe_allow_html=True)
        st.markdown(f'<div class="custom-card"><p class="card-body">{escape(result.future_outlook)}</p></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="risk-note">{escape(result.risk_notes)}</div>', unsafe_allow_html=True)
    with right:
        st.metric("盈利能力", f"{_score_to_100(result.scores.profitability)}/100")
        st.metric("存钱能力", f"{_score_to_100(result.scores.cash_saving)}/100")
        st.metric("未来潜力", f"{_score_to_100(result.scores.future_potential)}/100")
        st.markdown(f'<div class="custom-card"><p class="card-title">AI 判断</p><p class="card-body">{escape(result.sentiment_label)}</p></div>', unsafe_allow_html=True)
    st.markdown('<p class="section-title">企业健康雷达图</p>', unsafe_allow_html=True)
    st.plotly_chart(_build_radar_chart(result), use_container_width=True)
    st.markdown('<p class="section-title">近90天日线</p>', unsafe_allow_html=True)
    chart = _build_price_chart(snapshot)
    if chart.data:
        st.plotly_chart(chart, use_container_width=True)
    else:
        st.info("暂无日线数据。")
    st.markdown('<p class="section-title">核心财务数据</p>', unsafe_allow_html=True)
    _render_metrics_table(snapshot)


def _snapshot_for_compare_company(entry: dict) -> dict:
    code = str(entry.get("code") or "").strip()
    name = str(entry.get("name") or "").strip()
    if code:
        snapshot = build_company_snapshot(code)
        if snapshot.get("found"):
            return snapshot
    if name:
        snapshot = build_company_snapshot(name)
        if snapshot.get("found"):
            return snapshot
    return {"found": False, "company_name": name or code or "鏈煡鍏徃", "daily_prices": [], "financial_metrics": {}}


def _friendly_data_warning(raw: str) -> str:
    text = (raw or "").strip()
    if "AKShare" in text and ("失败" in text or "澶辫触" in text):
        return f"实时数据源本次请求未成功，系统已自动切换到兜底数据，页面仍可继续分析。{text}"
    if "日线" in text and ("失败" in text or "澶辫触" in text):
        return f"K线数据暂时不可用，已跳过走势图展示，不影响文本分析。{text}"
    return text


def _snapshot_for_compare_company(entry: dict) -> dict:
    code = str(entry.get("code") or "").strip()
    name = str(entry.get("name") or "").strip()
    if code:
        snapshot = build_company_snapshot(code)
        if snapshot.get("found"):
            return snapshot
    if name:
        snapshot = build_company_snapshot(name)
        if snapshot.get("found"):
            return snapshot
    return {"found": False, "company_name": name or code or "未知公司", "daily_prices": [], "financial_metrics": {}}


def _friendly_data_warning(raw: str) -> str:
    text = (raw or "").strip()
    lower = text.lower()
    if "akshare" in lower and ("失败" in text or "failure" in lower):
        return f"实时数据源本次请求失败，系统已自动切换到兜底数据，页面可继续使用。{text}"
    if ("日线" in text or "k线" in lower) and ("失败" in text or "failure" in lower):
        return f"K线数据暂时不可用，已跳过走势图展示，不影响文本分析。{text}"
    return text


def _render_compare_view(comparison: dict) -> None:
    company_a = comparison.get("company_a", {})
    company_b = comparison.get("company_b", {})
    snapshot_a = _snapshot_for_compare_company(company_a)
    snapshot_b = _snapshot_for_compare_company(company_b)

    st.markdown('<p class="section-title">对比结论</p>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="custom-card"><p class="card-title">当前领先：{escape(str(comparison.get("winner", "未知")))}</p><p class="card-body">原因：{escape(str(comparison.get("winner_reason", "综合评分更高")))}</p><p class="card-body">说明：{escape(str(comparison.get("industry_context", "")))}</p></div>',
        unsafe_allow_html=True,
    )

    st.markdown('<p class="section-title">双公司K线图（近90天）</p>', unsafe_allow_html=True)
    st.markdown(f"**{snapshot_a.get('company_name', '公司A')}**")
    chart_a = _build_price_chart(snapshot_a)
    if chart_a.data:
        st.plotly_chart(chart_a, use_container_width=True)
    else:
        st.info("公司A暂无K线数据。")
    st.markdown(f"**{snapshot_b.get('company_name', '公司B')}**")
    chart_b = _build_price_chart(snapshot_b)
    if chart_b.data:
        st.plotly_chart(chart_b, use_container_width=True)
    else:
        st.info("公司B暂无K线数据。")

    st.markdown('<p class="section-title">财务指标对比</p>', unsafe_allow_html=True)
    rows = comparison.get("rows") or []
    if rows:
        label_a = snapshot_a.get("company_name") or company_a.get("name") or "公司A"
        label_b = snapshot_b.get("company_name") or company_b.get("name") or "公司B"
        compare_df = pd.DataFrame(rows).rename(columns={"metric": "指标", "a": str(label_a), "b": str(label_b)})
        st.dataframe(compare_df, use_container_width=True, hide_index=True)
    else:
        st.info("暂无可展示的对比财务指标。")

    st.markdown('<p class="section-title">文字点评（对比）</p>', unsafe_allow_html=True)
    score_a = company_a.get("score")
    score_b = company_b.get("score")
    confidence = comparison.get("confidence_score", "N/A")
    limitations = comparison.get("limitations") or []
    limitation_text = "；".join(str(x) for x in limitations) if limitations else "当前对比基于可得财报数据，建议结合最新季报继续跟踪。"
    st.markdown(
        f'<div class="custom-card"><p class="card-body">从综合评分看，{escape(str(company_a.get("name", "公司A")))} 为 {escape(str(score_a))}，{escape(str(company_b.get("name", "公司B")))} 为 {escape(str(score_b))}。当前更优的是 {escape(str(comparison.get("winner", "未知")))}，核心依据是：{escape(str(comparison.get("winner_reason", "综合评分更高")))}。本次对比可信度约 {escape(str(confidence))}/100，主要限制：{escape(limitation_text)}</p></div>',
        unsafe_allow_html=True,
    )

    company_a_name = str(company_a.get("name", "公司A"))
    company_b_name = str(company_b.get("name", "公司B"))
    winner = str(comparison.get("winner", "未知"))
    winner_reason = str(comparison.get("winner_reason", "综合评分更高"))

    st.markdown('<p class="section-title">大白话分析（对比）</p>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="custom-card"><p class="card-body">把这两家公司放在一起看，关键是三件事：收入增速、利润增速、现金流质量。当前结论是 {escape(winner)} 暂时更占优，主要因为 {escape(winner_reason)}。如果把公司经营比作开店，就是谁不但客流增长快（收入），还能把钱真正留在手里（利润与现金流更一致），谁的经营质量更稳。{escape(company_a_name)} 和 {escape(company_b_name)} 的差异核心也在这里。</p></div>',
        unsafe_allow_html=True,
    )

    st.markdown('<p class="section-title">未来看法（对比）</p>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="custom-card"><p class="card-body">未来一年可以重点盯三条线：第一，收入增长是否还能持续；第二，净利润增速是否同步；第三，经营现金流是否跟上利润。若领先方后续能继续保持“收入扩张 + 利润改善 + 现金流不掉队”，优势会更稳；若其中一项明显走弱，当前领先关系可能反转。更稳妥的做法是每次新财报出来后，按同口径复盘一次这三项。</p></div>',
        unsafe_allow_html=True,
    )


def _run_query(query: str) -> None:
    if not query.strip():
        st.info("请输入公司简称、股票代码，或一句自然语言问题。")
        return
    context = context_from_state(st.session_state.get("conversation_context"))
    with st.spinner("正在识别并分析..."):
        agent_result = run_financial_agent(query, context_company_name=context.company_name, context_stock_code=context.stock_code)

    st.session_state["last_steps"] = [asdict(step) for step in agent_result.steps]
    st.session_state["last_suggested_questions"] = list(agent_result.suggested_questions or [])

    if agent_result.comparison:
        a = str(agent_result.comparison.get("company_a", {}).get("name") or "")
        b = str(agent_result.comparison.get("company_b", {}).get("name") or "")
        st.session_state["conversation_context"] = ConversationContext(company_name=a, stock_code="", compare_pair=[x for x in [a, b] if x], last_intent=agent_result.intent, last_query=agent_result.query, last_resolved_query=agent_result.resolved_query).to_dict()
    else:
        snapshot = agent_result.snapshot or {}
        company_name = str(snapshot.get("company_name") or "")
        stock_code = str(snapshot.get("stock_code") or "")
        if company_name == "通用问题模式" or stock_code == "N/A":
            company_name = ""
            stock_code = ""
        st.session_state["conversation_context"] = ConversationContext(
            company_name=company_name,
            stock_code=stock_code,
            compare_pair=[],
            last_intent=agent_result.intent,
            last_query=agent_result.query,
            last_resolved_query=agent_result.resolved_query,
        ).to_dict()

    snapshot = agent_result.snapshot or {}
    is_general_mode = (
        agent_result.intent == "通用财报问答"
        or str(snapshot.get("company_name") or "") == "通用问题模式"
        or str(snapshot.get("stock_code") or "") == "N/A"
    )
    if is_general_mode and agent_result.analysis is not None:
        answer_text = str(agent_result.analysis.plain_cashflow_summary or "").strip()
        if not answer_text:
            answer_text = "当前问题已进入通用模式，但暂时没有可展示的答案。"
        st.markdown('<p class="section-title">问题答案</p>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="custom-card"><p class="card-body">{escape(answer_text)}</p></div>',
            unsafe_allow_html=True,
        )
        return

    if agent_result.comparison:
        _render_compare_view(agent_result.comparison)
        with st.spinner("正在生成深度研究报告..."):
            _render_research_report(
                run_company_research_agent(
                    query,
                    context_company_name=context.company_name,
                    context_stock_code=context.stock_code,
                )
            )
    elif snapshot.get("found") and agent_result.analysis is not None:
        _render_analysis(snapshot, agent_result.analysis)
        with st.spinner("正在生成深度研究报告..."):
            _render_research_report(
                run_company_research_agent(
                    query,
                    context_company_name=context.company_name,
                    context_stock_code=context.stock_code,
                )
            )
    else:
        st.error(snapshot.get("data_warning") or "未识别到有效公司。")

    # 前端隐藏代理执行步骤
    # _render_agent_steps()
    _render_suggested_questions()


def main() -> None:
    st.set_page_config(page_title="上市公司分析AGENT", page_icon="📊", layout="wide", initial_sidebar_state="collapsed")
    apply_styles()
    _init_state()

    st.markdown(
        """
        <div class="hero">
            <h1>上市公司分析AGENT</h1>
            <p>用自然语言理解上市公司经营状况，结合财务数据与研究资料输出可复盘结论。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    default_query = "贵州茅台和宁德时代谁更好"
    with st.form("query_form"):
        query = st.text_input("输入你想了解的A股公司或问题", value=default_query, placeholder=default_query)
        submitted = st.form_submit_button("开始分析", type="primary", use_container_width=True)

    _render_context_bar()

    if submitted:
        _run_query(query)

    st.caption("免责声明：本工具不提供证券买卖建议，所有内容仅用于公开信息解读与学习参考。")


if __name__ == "__main__":
    main()
