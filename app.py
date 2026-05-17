from __future__ import annotations

from datetime import date
from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

from src.ai_client import analyze_company
from src.data_service import build_company_snapshot
from src.models import AnalysisResult


load_dotenv()


SOURCE_LABELS = {
    "akshare+sample": "公开接口 + 样例兜底",
    "akshare": "公开接口",
    "sample": "内置样例兜底",
    "akshare_lookup": "已识别公司，等待公开财务摘要",
    "not_found": "未识别",
}


def apply_styles() -> None:
    st.markdown(
        """
        <style>
        #MainMenu, footer, header {
            visibility: hidden;
            height: 0;
        }

        html, body, [data-testid="stAppViewContainer"], .stApp {
            background: #F5F7FA;
        }

        [data-testid="stHeader"] {
            background: transparent;
        }

        .block-container {
            max-width: 1180px;
            padding-top: 2rem;
            padding-bottom: 2.5rem;
        }

        .hero {
            text-align: center;
            margin: 0.2rem auto 1.5rem;
        }

        .hero h1 {
            color: #172033;
            font-size: 2.15rem;
            font-weight: 760;
            line-height: 1.2;
            margin: 0 0 0.45rem;
            letter-spacing: 0;
        }

        .hero p {
            color: #687385;
            font-size: 1rem;
            line-height: 1.7;
            margin: 0;
        }

        .custom-card {
            background: #FFFFFF;
            border: 1px solid rgba(226, 232, 240, 0.86);
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
            transition: transform 160ms ease, box-shadow 160ms ease, border-color 160ms ease;
            margin-bottom: 1rem;
        }

        .custom-card:hover {
            transform: translateY(-1px);
            border-color: rgba(45, 140, 240, 0.24);
            box-shadow: 0 8px 22px rgba(27, 39, 64, 0.08);
        }

        .input-card {
            background: #FFFFFF;
            border: 1px solid rgba(226, 232, 240, 0.86);
            border-radius: 12px;
            padding: 20px 20px 14px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
            margin-bottom: 1.3rem;
        }

        .section-title {
            color: #172033;
            font-size: 1.05rem;
            font-weight: 720;
            margin: 0 0 0.75rem;
        }

        .card-title {
            color: #172033;
            font-size: 1rem;
            font-weight: 720;
            margin: 0 0 0.65rem;
        }

        .card-body {
            color: #334155;
            font-size: 0.98rem;
            line-height: 1.85;
            margin: 0;
        }

        .company-card {
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            align-items: flex-start;
        }

        .company-name {
            color: #172033;
            font-size: 1.35rem;
            font-weight: 760;
            margin: 0 0 0.25rem;
        }

        .company-code {
            color: #697587;
            font-size: 0.92rem;
            margin: 0;
        }

        .sentiment-pill {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 5.5rem;
            border-radius: 999px;
            padding: 0.38rem 0.75rem;
            color: #0B6B4F;
            background: #E9F8F1;
            border: 1px solid #BFEBD6;
            font-weight: 700;
            white-space: nowrap;
        }

        .status-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.6rem;
            margin-top: 0.9rem;
        }

        .status-chip {
            border-radius: 10px;
            background: #F7FAFC;
            border: 1px solid #E6ECF3;
            padding: 0.68rem 0.75rem;
        }

        .status-chip span {
            display: block;
            color: #7A8495;
            font-size: 0.76rem;
            margin-bottom: 0.18rem;
        }

        .status-chip strong {
            display: block;
            color: #273449;
            font-size: 0.9rem;
            font-weight: 680;
            overflow-wrap: anywhere;
        }

        .score-card {
            background: #FFFFFF;
            border: 1px solid rgba(226, 232, 240, 0.92);
            border-radius: 12px;
            padding: 1rem;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
            margin-bottom: 0.75rem;
        }

        .score-label {
            color: #6B7484;
            font-size: 0.86rem;
            margin-bottom: 0.35rem;
        }

        .score-value {
            color: #172033;
            font-size: 1.8rem;
            line-height: 1.1;
            font-weight: 780;
        }

        .score-value small {
            color: #8A94A6;
            font-size: 0.9rem;
            font-weight: 600;
        }

        .risk-note {
            background: #FFF8E8;
            border: 1px solid #F4D99A;
            color: #72520A;
            border-radius: 12px;
            padding: 0.95rem 1rem;
            line-height: 1.75;
            font-weight: 620;
        }

        .empty-card {
            background: #FFFFFF;
            border: 1px dashed #C9D4E5;
            border-radius: 12px;
            padding: 1rem;
            color: #607086;
            text-align: center;
        }

        .risk-footer {
            color: #7A8495;
            font-size: 0.88rem;
            line-height: 1.7;
            text-align: center;
            margin-top: 1.6rem;
        }

        div[data-testid="stForm"] {
            background: #FFFFFF;
            border: 1px solid rgba(226, 232, 240, 0.86);
            border-radius: 12px;
            padding: 20px 20px 14px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        }

        div[data-testid="stTextInput"] label {
            color: #1F2A3D;
            font-weight: 680;
        }

        div[data-testid="stTextInput"] label p {
            color: #1F2A3D;
        }

        div[data-testid="stTextInput"] input {
            border-radius: 12px;
            border: 1px solid #D8E0EA;
            background: #FFFFFF;
            color: #172033;
            -webkit-text-fill-color: #172033;
            caret-color: #1677FF;
            min-height: 3rem;
        }

        div[data-testid="stTextInput"] input::placeholder {
            color: #6B7484;
            -webkit-text-fill-color: #6B7484;
            opacity: 1;
        }

        div[data-testid="stTextInput"] input:focus {
            border-color: #2D8CF0;
            box-shadow: 0 0 0 3px rgba(45, 140, 240, 0.13);
        }

        div[data-testid="stButton"] button,
        div[data-testid="stFormSubmitButton"] button {
            border-radius: 12px;
            min-height: 3rem;
            font-weight: 720;
            border: 0;
            background: linear-gradient(135deg, #2D8CF0 0%, #1677FF 100%);
            color: #FFFFFF;
            box-shadow: 0 6px 14px rgba(45, 140, 240, 0.22);
        }

        div[data-testid="stButton"] button:hover,
        div[data-testid="stFormSubmitButton"] button:hover {
            color: #FFFFFF;
            border: 0;
            box-shadow: 0 8px 18px rgba(45, 140, 240, 0.30);
        }

        div[data-testid="stMetric"] {
            background: transparent;
        }

        div[data-testid="stDataFrame"] {
            border: 1px solid #E5EBF3;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
        }

        div[data-testid="stPlotlyChart"] {
            background: #FFFFFF;
            border: 1px solid rgba(226, 232, 240, 0.92);
            border-radius: 12px;
            padding: 10px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        }

        div[data-testid="stExpander"] {
            background: #FFFFFF;
            border: 1px solid #E5EBF3;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
        }

        @media (max-width: 760px) {
            .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
                padding-top: 1.2rem;
            }

            .hero h1 {
                font-size: 1.58rem;
            }

            .company-card {
                display: block;
            }

            .sentiment-pill {
                margin-top: 0.75rem;
            }

            .status-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _score_to_100(value: float) -> int:
    return max(0, min(100, round(value * 10)))


def build_radar_chart(result: AnalysisResult) -> go.Figure:
    labels = ["赚钱能力", "存钱能力", "未来潜力"]
    values = [
        _score_to_100(result.scores.profitability),
        _score_to_100(result.scores.cash_saving),
        _score_to_100(result.scores.future_potential),
    ]

    fig = go.Figure(
        data=[
            go.Scatterpolar(
                r=values + [values[0]],
                theta=labels + [labels[0]],
                fill="toself",
                name="企业健康度",
                line=dict(color="#2D8CF0", width=3),
                fillcolor="rgba(45, 140, 240, 0.20)",
            )
        ]
    )
    fig.update_layout(
        margin=dict(l=24, r=24, t=18, b=18),
        height=340,
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickfont=dict(size=10, color="#8A94A6"),
                gridcolor="#E1E8F2",
                linecolor="#D6DFEA",
            ),
            angularaxis=dict(tickfont=dict(size=13, color="#334155"), gridcolor="#E1E8F2"),
        ),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def build_daily_price_chart(snapshot: dict) -> go.Figure:
    prices = pd.DataFrame(snapshot.get("daily_prices") or [])
    fig = go.Figure()
    if not prices.empty:
        prices["date"] = pd.to_datetime(prices["date"], errors="coerce")
        prices = prices.dropna(subset=["date", "open", "high", "low", "close"]).sort_values("date")
        for window in [5, 10, 20]:
            prices[f"ma{window}"] = prices["close"].rolling(window=window, min_periods=window).mean()

        today = pd.Timestamp(date.today())
        display_start = today - pd.Timedelta(days=90)
        display_prices = prices[(prices["date"] >= display_start) & (prices["date"] <= today)].copy()
        if display_prices.empty:
            display_prices = prices.tail(60).copy()

        display_prices["date_label"] = display_prices["date"].dt.strftime("%Y-%m-%d")
        fig.add_trace(
            go.Candlestick(
                x=display_prices["date_label"],
                open=display_prices["open"],
                high=display_prices["high"],
                low=display_prices["low"],
                close=display_prices["close"],
                increasing_line_color="#E84A5F",
                decreasing_line_color="#13A579",
                increasing_fillcolor="rgba(232, 74, 95, 0.50)",
                decreasing_fillcolor="rgba(19, 165, 121, 0.50)",
                whiskerwidth=0.4,
                name="日线",
            )
        )

        ma_styles = {
            5: ("MA5", "#F59E0B", 2.0),
            10: ("MA10", "#2D8CF0", 2.0),
            20: ("MA20", "#8B5CF6", 2.0),
        }
        for window, (name, color, width) in ma_styles.items():
            fig.add_trace(
                go.Scatter(
                    x=display_prices["date_label"],
                    y=display_prices[f"ma{window}"],
                    mode="lines",
                    line=dict(color=color, width=width),
                    name=name,
                    connectgaps=False,
                )
            )

    fig.update_layout(
        height=360,
        margin=dict(l=12, r=12, t=34, b=8),
        xaxis=dict(
            showgrid=False,
            rangeslider=dict(visible=False),
            tickfont=dict(color="#6B7484", size=11),
            type="category",
            nticks=8,
        ),
        yaxis=dict(
            title=dict(text="价格", font=dict(color="#6B7484", size=11)),
            tickfont=dict(color="#6B7484", size=11),
            gridcolor="#EEF2F7",
            fixedrange=False,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.04,
            xanchor="left",
            x=0,
            font=dict(size=10, color="#334155"),
            bgcolor="rgba(255,255,255,0.72)",
        ),
        hovermode="x unified",
        showlegend=True,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def render_metric_table(snapshot: dict) -> None:
    metrics = snapshot["financial_metrics"]
    rows = [
        ("报告期", metrics.get("report_period")),
        ("营业收入", metrics.get("revenue")),
        ("净利润", metrics.get("net_profit")),
        ("经营现金流", metrics.get("operating_cash_flow")),
        ("营收同比", metrics.get("revenue_yoy")),
        ("净利润同比", metrics.get("net_profit_yoy")),
    ]
    table = pd.DataFrame(rows, columns=["指标", "数值"]).fillna("暂无")
    st.dataframe(table, use_container_width=True, hide_index=True)


def render_status(snapshot: dict, result: AnalysisResult) -> None:
    metrics = snapshot.get("financial_metrics", {})
    source_label = SOURCE_LABELS.get(snapshot["data_source"], snapshot["data_source"])
    st.markdown(
        f"""
        <div class="custom-card">
            <div class="company-card">
                <div>
                    <p class="company-name">{escape(snapshot["company_name"])} ({escape(snapshot["stock_code"])})</p>
                </div>
                <div class="sentiment-pill">{escape(result.sentiment_label)}</div>
            </div>
            <div class="status-grid">
                <div class="status-chip"><span>数据来源</span><strong>{escape(source_label)}</strong></div>
                <div class="status-chip"><span>报告期</span><strong>{escape(str(metrics.get("report_period", "暂无")))}</strong></div>
                <div class="status-chip"><span>AI 判断</span><strong>{escape(result.sentiment_label)}</strong></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_daily_price_chart(snapshot: dict) -> None:
    st.markdown('<p class="section-title">近90天日线走势</p>', unsafe_allow_html=True)
    if snapshot.get("daily_prices"):
        st.plotly_chart(build_daily_price_chart(snapshot), use_container_width=True)
    else:
        warning = snapshot.get("price_warning") or "暂未获取到近期日线行情。"
        st.markdown(
            f"""
            <div class="custom-card">
                <p class="card-body">{escape(warning)}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_score_strip(result: AnalysisResult) -> None:
    scores = [
        ("赚钱能力", result.scores.profitability),
        ("存钱能力", result.scores.cash_saving),
        ("未来潜力", result.scores.future_potential),
    ]
    for label, score in scores:
        st.markdown(
            f"""
            <div class="score-card">
                <div class="score-label">{escape(label)}</div>
                <div class="score-value">{_score_to_100(score)} <small>/ 100</small></div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_text_card(title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="custom-card">
            <p class="card-title">{escape(title)}</p>
            <p class="card-body">{escape(body)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_not_found(snapshot: dict) -> None:
    st.error(snapshot["data_warning"])
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            """
            <div class="custom-card">
                <p class="card-title">可以输入完整公司简称</p>
                <p class="card-body">例如：贵州茅台、平安银行、万科A、格力电器。</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            """
            <div class="custom-card">
                <p class="card-title">也可以输入 6 位股票代码</p>
                <p class="card-body">例如：000001、600519、000651。</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_analysis(result: AnalysisResult, snapshot: dict) -> None:
    render_status(snapshot, result)
    if snapshot.get("data_warning"):
        st.warning(snapshot["data_warning"])
    render_daily_price_chart(snapshot)

    left_col, right_col = st.columns([7, 3], gap="large")
    with left_col:
        render_text_card("白话解读", result.plain_cashflow_summary)
        render_text_card("未来一年怎么看", result.future_outlook)
        st.markdown(
            f"""
            <div class="risk-note">
                {escape(result.risk_notes)}
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right_col:
        st.markdown('<p class="section-title">企业健康度</p>', unsafe_allow_html=True)
        render_score_strip(result)
        st.markdown(
            f"""
            <div class="custom-card">
                <p class="card-title">AI 情绪指示器</p>
                <p class="card-body">当前倾向：<strong>{escape(result.sentiment_label)}</strong></p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<p class="section-title">企业健康度雷达图</p>', unsafe_allow_html=True)
    st.plotly_chart(build_radar_chart(result), use_container_width=True)

    st.markdown('<p class="section-title">核心财务数据</p>', unsafe_allow_html=True)
    render_metric_table(snapshot)


def run_query(query: str) -> None:
    if not query.strip():
        st.info("请输入公司简称、股票代码，或一句自然语言问题。")
        return
    with st.spinner("正在识别公司、抓取财务数据并生成白话解读..."):
        snapshot = build_company_snapshot(query)
        result = analyze_company(snapshot, query) if snapshot.get("found") else None
    if snapshot.get("found") and result is not None:
        render_analysis(result, snapshot)
    else:
        render_not_found(snapshot)


def main() -> None:
    st.set_page_config(
        page_title="大白话财报",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    apply_styles()

    st.markdown(
        """
        <div class="hero">
            <h1>大白话财报 - 你的 AI 消费级投顾</h1>
            <p>用自然语言看懂 A 股财报，把复杂数据翻译成普通人也能判断的经营信号。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    example = "帮我看看贵州茅台最近赚不赚钱，未来怎么样？"
    with st.form("query_form"):
        query = st.text_input("输入你想了解的 A 股公司或问题", value=example, placeholder=example)
        form_cols = st.columns([0.24, 0.76])
        with form_cols[0]:
            submitted = st.form_submit_button("开始分析", type="primary", use_container_width=True)
        with form_cols[1]:
            st.caption("示例：贵州茅台、平安银行、万科A、格力电器、000001、600519")

    if submitted:
        run_query(query)
    else:
        st.markdown(
            """
            <div class="empty-card">
                输入公司简称或股票代码后点击“开始分析”，即可查看白话解读、评分和雷达图。
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="risk-footer">免责声明：本工具不提供证券买卖建议，所有内容仅为公开信息解读与学习参考。股票投资有风险，不构成投资建议。</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
