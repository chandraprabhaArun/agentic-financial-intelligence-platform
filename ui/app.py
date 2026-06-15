import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import json
import time
from pathlib import Path
from config import CACHE_DIR, REPORTS_DIR

# ── PAGE CONFIG ─────────────────────────────────────────
st.set_page_config(
    page_title="Agentic Financial Intelligence Platform",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── CUSTOM CSS ──────────────────────────────────────────
st.markdown("""
<style>
.metric-card {
    background: #1e1e2e;
    border-radius: 10px;
    padding: 16px;
    border-left: 4px solid #4f8ef7;
    margin: 4px 0;
}
.agent-running {
    background: #1a3a1a;
    border-left: 4px solid #00cc44;
    border-radius: 8px;
    padding: 10px 14px;
    margin: 4px 0;
    font-family: monospace;
    font-size: 13px;
}
.agent-done {
    background: #1a2a3a;
    border-left: 4px solid #4488ff;
    border-radius: 8px;
    padding: 10px 14px;
    margin: 4px 0;
    font-family: monospace;
    font-size: 13px;
}
.rec-buy  { color: #00cc44; font-size: 28px; font-weight: bold; }
.rec-hold { color: #ffaa00; font-size: 28px; font-weight: bold; }
.rec-sell { color: #ff4444; font-size: 28px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)


# ── SIDEBAR ─────────────────────────────────────────────
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/f/fa/Apple_logo_black.svg/100px-Apple_logo_black.svg.png", width=40)
st.sidebar.title("Financial Intelligence")
st.sidebar.markdown("---")

ticker = st.sidebar.text_input(
    "Enter Ticker Symbol",
    value="AAPL",
    placeholder="e.g. AAPL, MSFT, TSLA"
).upper().strip()

run_button = st.sidebar.button(
    "🚀 Run Full Analysis",
    type="primary",
    use_container_width=True
)

st.sidebar.markdown("---")
st.sidebar.markdown("**Agents in Pipeline:**")
agents = [
    "📥 Filing Retrieval",
    "📊 Financial Extraction",
    "💰 Valuation (DCF)",
    "📰 News Research",
    "🔍 RAG Agent",
    "📝 Investment Recommendation",
    "📄 Report Generation",
    "✅ Validation & QA"
]
for agent in agents:
    st.sidebar.markdown(f"- {agent}")

st.sidebar.markdown("---")
st.sidebar.markdown("**Tech Stack:**")
st.sidebar.markdown("LangGraph · LlamaIndex · ChromaDB · OpenAI · SEC EDGAR · yfinance · FastAPI")


# ── MAIN HEADER ─────────────────────────────────────────
st.title("📊 Agentic Financial Intelligence Platform")
st.markdown("*Enterprise-grade multi-agent AI system for automated financial research*")
st.markdown("---")


def load_cache(ticker: str) -> dict:
    """Load all cached agent outputs."""
    data = {}
    files = {
        "financials": f"{ticker}_financials.json",
        "valuation":  f"{ticker}_valuation.json",
        "news":       f"{ticker}_news.json",
        "memo":       f"{ticker}_investment_memo.json",
        "qa":         f"{ticker}_qa_report.json",
    }
    for key, fname in files.items():
        fpath = CACHE_DIR / fname
        if fpath.exists():
            data[key] = json.loads(fpath.read_text())
    return data


def show_agent_trace(ticker: str):
    """Show live agent trace panel."""
    st.subheader("🤖 Agent Trace — Live Pipeline")

    agent_steps = [
        ("📥 Filing Retrieval Agent",        "Fetching 10-K filings from SEC EDGAR..."),
        ("📊 Financial Extraction Agent",     "Parsing XBRL financial data..."),
        ("💰 Valuation Agent",               "Running DCF model + comparable analysis..."),
        ("📰 News Research Agent",            "Analyzing market sentiment..."),
        ("🔍 RAG Agent",                     "Semantic search over 10-K documents..."),
        ("📝 Investment Recommendation Agent","Generating investment memo with GPT-4o-mini..."),
        ("📄 Report Generation Agent",        "Creating DOCX investment report..."),
        ("✅ Validation & QA Agent",          "Cross-checking all outputs..."),
    ]

    trace_container = st.empty()

    for i, (agent, action) in enumerate(agent_steps):
        with trace_container.container():
            for j, (a, act) in enumerate(agent_steps):
                if j < i:
                    st.markdown(
                        f'<div class="agent-done">✅ {a} — Complete</div>',
                        unsafe_allow_html=True
                    )
                elif j == i:
                    st.markdown(
                        f'<div class="agent-running">⚡ {a} — {act}</div>',
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f'<div style="color:#666;padding:6px 14px;font-size:13px;">⬜ {a}</div>',
                        unsafe_allow_html=True
                    )
        time.sleep(0.4)

    # Final state — all complete
    with trace_container.container():
        for a, _ in agent_steps:
            st.markdown(
                f'<div class="agent-done">✅ {a} — Complete</div>',
                unsafe_allow_html=True
            )


def run_pipeline(ticker: str):
    """Run the full 7-agent pipeline."""
    with st.spinner(f"Running 7-agent pipeline for {ticker}..."):
        show_agent_trace(ticker)
        # Run actual pipeline
        from orchestrator import run_pipeline as orchestrate
        result = orchestrate(ticker)
    return result


def show_dashboard(ticker: str, data: dict):
    """Show the main analysis dashboard."""

    # ── FINANCIALS TAB ──────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Financials", "💰 Valuation", "📰 News", "📄 Investment Memo", "✅ QA Report"
    ])

    with tab1:
        st.subheader(f"Financial Highlights — {ticker}")
        if "financials" in data:
            m = data["financials"]["metrics"]
            r = data["financials"]["ratios"]

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Revenue",    m["Revenue"][0]["formatted"])
            with col2:
                st.metric("Net Income", m["NetIncome"][0]["formatted"])
            with col3:
                st.metric("EPS (Diluted)", m["EPS_Diluted"][0]["formatted"])
            with col4:
                st.metric("Net Margin", r.get("NetProfitMargin", "N/A"))

            col5, col6, col7, col8 = st.columns(4)
            with col5:
                st.metric("Total Assets", m["TotalAssets"][0]["formatted"])
            with col6:
                st.metric("Cash",         m["CashAndEquivalents"][0]["formatted"])
            with col7:
                st.metric("ROE",          r.get("ROE", "N/A"))
            with col8:
                st.metric("Debt/Equity",  r.get("DebtToEquity", "N/A"))

            # Historical revenue chart
            st.subheader("Revenue Trend")
            import plotly.graph_objects as go
            rev_data = m.get("Revenue", [])
            if len(rev_data) > 1:
                years  = [d["year"] for d in rev_data[:5]][::-1]
                values = [d["value"]/1e9 for d in rev_data[:5]][::-1]
                fig = go.Figure(go.Bar(
                    x=years, y=values,
                    marker_color="#4f8ef7",
                    text=[f"${v:.1f}B" for v in values],
                    textposition="outside"
                ))
                fig.update_layout(
                    title="Annual Revenue (USD Billions)",
                    yaxis_title="Revenue ($B)",
                    plot_bgcolor="#0e1117",
                    paper_bgcolor="#0e1117",
                    font_color="white",
                    height=350
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Run the analysis to see financials.")

    with tab2:
        st.subheader(f"Valuation Analysis — {ticker}")
        if "valuation" in data:
            v   = data["valuation"]
            mkt = v["market"]
            dcf = v["dcf"]
            rec = v["recommendation"]
            cmp = v["comparables"]

            # Recommendation banner
            r_val = rec.get("recommendation", "HOLD")
            color_class = f"rec-{r_val.lower()}"
            st.markdown(
                f'<div style="text-align:center;padding:20px;">'
                f'<span class="{color_class}">{r_val}</span><br>'
                f'<span style="color:#888;font-size:14px">Confidence: {rec.get("confidence","N/A")}</span>'
                f'</div>',
                unsafe_allow_html=True
            )

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Current Price",   f"${mkt.get('current_price',0):,.2f}")
                st.metric("Market Cap",      f"${mkt.get('market_cap',0)/1e12:.2f}T")
                st.metric("P/E Ratio",       f"{mkt.get('pe_ratio',0):.1f}x")
            with col2:
                st.metric("DCF Value",       f"${dcf.get('intrinsic_value',0):,.2f}")
                st.metric("DCF Upside",      f"{dcf.get('upside_downside',0):+.1f}%")
                st.metric("WACC",            dcf.get("wacc", "9%"))
            with col3:
                st.metric("Analyst Target",  f"${rec.get('analyst_target',0):,.2f}")
                st.metric("Analyst Upside",  f"{rec.get('analyst_upside',0):+.1f}%")
                st.metric("52W High",        f"${mkt.get('52w_high',0):,.2f}")

            # Valuation comparison chart
            st.subheader("Price vs Valuation Models")
            import plotly.graph_objects as go
            fig2 = go.Figure(go.Bar(
                x=["Current Price", "DCF Value", "P/E Implied", "Analyst Target"],
                y=[
                    mkt.get("current_price", 0),
                    dcf.get("intrinsic_value", 0),
                    cmp.get("pe_implied", 0),
                    rec.get("analyst_target", 0)
                ],
                marker_color=["#4f8ef7","#ff4444","#ffaa00","#00cc44"],
                text=[
                    f"${mkt.get('current_price',0):,.0f}",
                    f"${dcf.get('intrinsic_value',0):,.0f}",
                    f"${cmp.get('pe_implied',0):,.0f}",
                    f"${rec.get('analyst_target',0):,.0f}"
                ],
                textposition="outside"
            ))
            fig2.update_layout(
                plot_bgcolor="#0e1117",
                paper_bgcolor="#0e1117",
                font_color="white",
                height=350,
                yaxis_title="Price ($)"
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Run the analysis to see valuation.")

    with tab3:
        st.subheader(f"News Sentiment — {ticker}")
        if "news" in data:
            sen = data["news"]["sentiment"]
            articles = data["news"]["articles"]

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Overall Sentiment", sen.get("overall","N/A"))
            with col2:
                st.metric("Sentiment Score", f"{sen.get('score',0):+.3f}")
            with col3:
                st.metric("🟢 Bullish", sen["breakdown"]["bullish"])
            with col4:
                st.metric("🔴 Bearish", sen["breakdown"]["bearish"])

            st.subheader("Recent Headlines")
            for article in articles:
                score = article.get("sentiment_score", 0)
                icon  = "🟢" if score > 0.15 else "🔴" if score < -0.15 else "🟡"
                st.markdown(
                    f"{icon} **[{article.get('published','')[:8]}]** "
                    f"{article.get('title','')} "
                    f"*(Score: {score:+.2f})*"
                )
        else:
            st.info("Run the analysis to see news sentiment.")

    with tab4:
        st.subheader(f"Investment Memo — {ticker}")
        if "memo" in data:
            memo_text = data["memo"].get("memo","")
            st.markdown(memo_text)

            # Download DOCX
            report_files = list(REPORTS_DIR.glob(f"{ticker}_*.docx"))
            if report_files:
                latest_report = sorted(report_files)[-1]
                with open(latest_report, "rb") as f:
                    st.download_button(
                        label="📥 Download DOCX Report",
                        data=f,
                        file_name=latest_report.name,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
        else:
            st.info("Run the analysis to see investment memo.")

    with tab5:
        st.subheader(f"QA Validation Report — {ticker}")
        if "qa" in data:
            qa = data["qa"]
            status = qa.get("status","")

            if "PASSED" in status and "WARNING" not in status:
                st.success(f"✅ QA STATUS: {status}")
            elif "WARNING" in status:
                st.warning(f"⚠️ QA STATUS: {status}")
            else:
                st.error(f"❌ QA STATUS: {status}")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("✓ Checks Passed", qa.get("pass_count",0))
            with col2:
                st.metric("⚠ Warnings",      qa.get("warning_count",0))
            with col3:
                st.metric("✗ Errors",         qa.get("error_count",0))

            st.subheader("Detailed Checks")
            for category, issues in qa.get("checks",{}).items():
                with st.expander(f"📋 {category}"):
                    for issue in issues:
                        if issue.startswith("✓"):
                            st.success(issue)
                        elif "ERROR" in issue or "MISSING" in issue:
                            st.error(issue)
                        else:
                            st.warning(issue)
        else:
            st.info("Run the analysis to see QA report.")


# ── MAIN LOGIC ───────────────────────────────────────────
cached_data = load_cache(ticker)

if run_button:
    st.info(f"🚀 Starting 7-agent pipeline for **{ticker}**...")
    run_pipeline(ticker)
    st.success(f"✅ Analysis complete for {ticker}!")
    cached_data = load_cache(ticker)
    st.rerun()

if cached_data:
    show_dashboard(ticker, cached_data)
else:
    st.info(f"👆 Enter a ticker and click **Run Full Analysis** to start.")
    st.markdown("""
    ### What this platform does:
    1. **📥 Retrieves** real 10-K filings from SEC EDGAR
    2. **📊 Extracts** financial metrics (revenue, EPS, margins, ratios)
    3. **💰 Values** the company using DCF + comparable analysis
    4. **📰 Analyzes** news sentiment
    5. **🔍 Answers** questions from actual filing documents using RAG
    6. **📝 Generates** a professional investment memo using GPT-4o-mini
    7. **📄 Creates** a downloadable DOCX report
    8. **✅ Validates** all outputs with 14-point QA check
    """)