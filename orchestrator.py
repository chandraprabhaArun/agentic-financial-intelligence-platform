import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from agents.filing_retrieval     import run as filing_run
from agents.financial_extraction import run as extraction_run
from agents.valuation            import run as valuation_run
from agents.news_research        import run as news_run
from agents.rag_agent            import run as rag_run
from agents.investment_rec       import run as investment_run
from agents.report_generation    import run as report_run
from agents.validation_qa        import run as qa_run


# ─────────────────────────────────────────────
#  SHARED STATE
# ─────────────────────────────────────────────
class FinancialState(TypedDict):
    ticker:      str
    filings:     Optional[list]
    financials:  Optional[dict]
    valuation:   Optional[dict]
    news:        Optional[dict]
    rag:         Optional[dict]
    memo:        Optional[dict]
    report:      Optional[dict]
    qa:          Optional[dict]
    errors:      Optional[list]
    status:      Optional[str]


# ─────────────────────────────────────────────
#  AGENT NODES
# ─────────────────────────────────────────────
def filing_node(state: FinancialState) -> FinancialState:
    print("\n🔵 [Node 1/7] Filing Retrieval Agent...")
    try:
        filings, paths = filing_run(state["ticker"])
        return {**state, "filings": filings, "status": "filings_complete"}
    except Exception as e:
        errors = state.get("errors") or []
        return {**state, "errors": errors + [f"FilingAgent: {e}"],
                "status": "filing_failed"}


def extraction_node(state: FinancialState) -> FinancialState:
    print("\n🔵 [Node 2/7] Financial Extraction Agent...")
    try:
        financials = extraction_run(state["ticker"])
        return {**state, "financials": financials, "status": "extraction_complete"}
    except Exception as e:
        errors = state.get("errors") or []
        return {**state, "errors": errors + [f"ExtractionAgent: {e}"],
                "status": "extraction_failed"}


def valuation_node(state: FinancialState) -> FinancialState:
    print("\n🔵 [Node 3/7] Valuation Agent...")
    try:
        valuation = valuation_run(state["ticker"])
        return {**state, "valuation": valuation, "status": "valuation_complete"}
    except Exception as e:
        errors = state.get("errors") or []
        return {**state, "errors": errors + [f"ValuationAgent: {e}"],
                "status": "valuation_failed"}


def news_node(state: FinancialState) -> FinancialState:
    print("\n🔵 [Node 4/7] News Research Agent...")
    try:
        news = news_run(state["ticker"])
        return {**state, "news": news, "status": "news_complete"}
    except Exception as e:
        errors = state.get("errors") or []
        return {**state, "errors": errors + [f"NewsAgent: {e}"],
                "status": "news_failed"}


def rag_node(state: FinancialState) -> FinancialState:
    print("\n🔵 [Node 5/7] RAG Agent...")
    try:
        rag = rag_run(state["ticker"])
        return {**state, "rag": rag, "status": "rag_complete"}
    except Exception as e:
        errors = state.get("errors") or []
        return {**state, "errors": errors + [f"RAGAgent: {e}"],
                "status": "rag_failed"}


def investment_node(state: FinancialState) -> FinancialState:
    print("\n🔵 [Node 6/7] Investment Recommendation Agent...")
    try:
        memo = investment_run(state["ticker"])
        return {**state, "memo": memo, "status": "investment_complete"}
    except Exception as e:
        errors = state.get("errors") or []
        return {**state, "errors": errors + [f"InvestmentAgent: {e}"],
                "status": "investment_failed"}


def report_node(state: FinancialState) -> FinancialState:
    print("\n🔵 [Node 7/7] Report Generation + Validation Agent...")
    try:
        report = report_run(state["ticker"])
        qa     = qa_run(state["ticker"])
        return {**state, "report": report, "qa": qa, "status": "complete"}
    except Exception as e:
        errors = state.get("errors") or []
        return {**state, "errors": errors + [f"ReportAgent: {e}"],
                "status": "report_failed"}


def summary_node(state: FinancialState) -> FinancialState:
    """Final summary printed after all agents complete."""
    ticker = state["ticker"]
    print(f"\n{'='*60}")
    print(f"  🏁 FINAL PIPELINE SUMMARY — {ticker}")
    print(f"{'='*60}")

    if state.get("financials"):
        m = state["financials"]["metrics"]
        r = state["financials"]["ratios"]
        print(f"\n  📊 FINANCIALS")
        print(f"     Revenue:    {m['Revenue'][0]['formatted']}")
        print(f"     Net Income: {m['NetIncome'][0]['formatted']}")
        print(f"     EPS:        {m['EPS_Diluted'][0]['formatted']}")
        print(f"     Margin:     {r.get('NetProfitMargin','N/A')}")

    if state.get("valuation"):
        v   = state["valuation"]
        rec = v["recommendation"]
        dcf = v["dcf"]
        print(f"\n  💰 VALUATION")
        print(f"     Price:      ${v['market']['current_price']:,.2f}")
        print(f"     DCF Value:  ${dcf['intrinsic_value']:,.2f}  ({dcf['upside_downside']:+.1f}%)")
        print(f"     Rating:     {rec['color']} {rec['recommendation']} (Confidence: {rec['confidence']})")

    if state.get("news"):
        s = state["news"]["sentiment"]
        print(f"\n  📰 NEWS SENTIMENT")
        print(f"     {s['emoji']} {s['overall']}  (score: {s['score']:+.3f})")

    if state.get("qa"):
        qa = state["qa"]
        print(f"\n  ✅ QA VALIDATION")
        print(f"     Status:   {qa['status']}")
        print(f"     Passed:   {qa['pass_count']} checks")
        print(f"     Warnings: {qa['warning_count']}")
        print(f"     Errors:   {qa['error_count']}")

    if state.get("report"):
        print(f"\n  📄 REPORT")
        print(f"     DOCX: {state['report'].get('docx_path','').split(chr(92))[-1]}")

    if state.get("errors"):
        print(f"\n  ⚠️  ERRORS: {state['errors']}")

    print(f"\n{'='*60}")
    print(f"  ✅ All 7 agents completed successfully!")
    print(f"{'='*60}\n")

    return {**state, "status": "pipeline_complete"}


# ─────────────────────────────────────────────
#  CONDITIONAL EDGES
# ─────────────────────────────────────────────
def should_run_valuation(state: FinancialState) -> str:
    if state.get("status") == "extraction_failed":
        return "skip_valuation"
    return "run_valuation"


def should_run_investment(state: FinancialState) -> str:
    if state.get("status") in ["rag_failed", "news_failed"]:
        return "skip_investment"
    return "run_investment"


# ─────────────────────────────────────────────
#  BUILD THE GRAPH
# ─────────────────────────────────────────────
def build_graph() -> StateGraph:
    graph = StateGraph(FinancialState)

    graph.add_node("filing_agent",     filing_node)
    graph.add_node("extraction_agent", extraction_node)
    graph.add_node("valuation_agent",  valuation_node)
    graph.add_node("news_agent",       news_node)
    graph.add_node("rag_agent",        rag_node)
    graph.add_node("investment_agent", investment_node)
    graph.add_node("report_agent",     report_node)
    graph.add_node("summary_agent",    summary_node)

    graph.set_entry_point("filing_agent")
    graph.add_edge("filing_agent", "extraction_agent")

    graph.add_conditional_edges(
        "extraction_agent",
        should_run_valuation,
        {
            "run_valuation":  "valuation_agent",
            "skip_valuation": "news_agent"
        }
    )

    graph.add_edge("valuation_agent",  "news_agent")
    graph.add_edge("news_agent",       "rag_agent")

    graph.add_conditional_edges(
        "rag_agent",
        should_run_investment,
        {
            "run_investment":  "investment_agent",
            "skip_investment": "report_agent"
        }
    )

    graph.add_edge("investment_agent", "report_agent")
    graph.add_edge("report_agent",     "summary_agent")
    graph.add_edge("summary_agent",    END)

    return graph.compile()


# ─────────────────────────────────────────────
#  RUN
# ─────────────────────────────────────────────
def run_pipeline(ticker: str = "AAPL") -> dict:
    print(f"\n{'='*60}")
    print(f"  🚀 AGENTIC FINANCIAL INTELLIGENCE PLATFORM")
    print(f"  Ticker: {ticker} | Agents: 7 | Framework: LangGraph")
    print(f"{'='*60}")

    graph = build_graph()

    initial_state: FinancialState = {
        "ticker":     ticker,
        "filings":    None,
        "financials": None,
        "valuation":  None,
        "news":       None,
        "rag":        None,
        "memo":       None,
        "report":     None,
        "qa":         None,
        "errors":     [],
        "status":     "starting"
    }

    final_state = graph.invoke(initial_state)
    return final_state


if __name__ == "__main__":
    run_pipeline("AAPL")