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

load_dotenv()


def apply_styles() -> None:
    st.markdown(
        """
        <style>
        #MainMenu, footer, header { visibility: hidden; height: 0; }
        html, body, [data-testid="stAppViewContainer"], .stApp { background: #F5F7FA; }
        .block-container { max-width: 1180px; padding-top: 2rem; padding-bottom: 2.5rem; }
        .hero { text-align: center; margin: 0.2rem auto 1.2rem; }
        .hero h1 { color: #172033; font-size: 2.1rem; font-weight: 760; margin: 0 0 0.45rem; letter-spacing: 0; }
        .hero p { color: #687385; font-size: 0.98rem; line-height: 1.8; margin: 0; }
        .custom-card {
            background: #FFFFFF; border: 1px solid rgba(226, 232, 240, 0.86);
            border-radius: 12px; padding: 16px 18px; margin-bottom: 0.9rem;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        }
        .card-title { color: #172033; font-size: 1rem; font-weight: 720; margin: 0 0 0.5rem; }
        .card-body { color: #334155; font-size: 0.96rem; line-height: 1.8; margin: 0; }
        .section-title { color: #172033; font-size: 1.05rem; font-weight: 720; margin: 0.2rem 0 0.7rem; }
        .context-main { color: #1F2A3D; font-weight: 700; font-size: 1.55rem; }
        .risk-note { background: #FFF8E8; border: 1px solid #F4D99A; color: #72520A; border-radius: 12px; padding: 0.9rem 1rem; line-height: 1.75; font-weight: 620; }
        div[data-testid="stForm"] {
            background: #FFFFFF; border: 1px solid rgba(226, 232, 240, 0.86);
            border-radius: 12px; padding: 18px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        }
        div[data-testid="stButton"] button, div[data-testid="stFormSubmitButton"] button {
            border-radius: 12px; min-height: 3rem; font-weight: 720; border: 0;
            background: linear-gradient(135deg, #2D8CF0 0%, #1677FF 100%); color: #FFFFFF;
            box-shadow: 0 6px 14px rgba(45, 140, 240, 0.22);
        }
        div[data-testid="stDataFrame"], div[data-testid="stPlotlyChart"], div[data-testid="stExpander"] {
            border: 1px solid #E5EBF3; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
        }
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
        yaxis=dict(title=dict(text="价格"), gridcolor="#EEF2F7"),
        legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="left", x=0),
        hovermode="x unified",
        showlegend=True,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
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


def _render_analysis(snapshot: dict, result: AnalysisResult) -> None:
    st.success(f"公司：{snapshot.get('company_name')}（{snapshot.get('stock_code')}）")
    if snapshot.get("data_warning"):
        st.warning(snapshot.get("data_warning"))
    if snapshot.get("price_warning"):
        st.warning(snapshot.get("price_warning"))
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
    return {"found": False, "company_name": name or code or "未知公司", "daily_prices": [], "financial_metrics": {}}


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
    if agent_result.comparison:
        _render_compare_view(agent_result.comparison)
    elif snapshot.get("found") and agent_result.analysis is not None:
        _render_analysis(snapshot, agent_result.analysis)
    else:
        st.error(snapshot.get("data_warning") or "未识别到有效公司。")

    _render_agent_steps()
    _render_suggested_questions()


def main() -> None:
    st.set_page_config(page_title="大白话财报", page_icon="📊", layout="wide", initial_sidebar_state="collapsed")
    apply_styles()
    _init_state()

    st.markdown(
        """
        <div class="hero">
            <h1>大白话财报 - 你的 AI 消费级投研</h1>
            <p>用自然语言看懂 A 股财报，把复杂的数据翻译成普通人也能判断的经营信号。</p>
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
