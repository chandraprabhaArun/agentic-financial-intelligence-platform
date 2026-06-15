import sys
import os
from agents.rag_agent import run as rag_run
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from agents.filing_retrieval    import run as filing_run
from agents.financial_extraction import run as extraction_run
from agents.valuation           import run as valuation_run
from agents.news_research       import run as news_run


# ─────────────────────────────────────────────
#  SHARED STATE — every agent reads & writes this
# ─────────────────────────────────────────────
class FinancialState(TypedDict):
    ticker:       str
    filings:      Optional[list]
    financials:   Optional[dict]
    valuation:    Optional[dict]
    news:         Optional[dict]
    rag:          Optional[dict]
    errors:       Optional[list]
    status:       Optional[str]


# ─────────────────────────────────────────────
#  AGENT NODES
# ─────────────────────────────────────────────
def filing_node(state: FinancialState) -> FinancialState:
    print("\n🔵 [Node 1/4] Filing Retrieval Agent running...")
    try:
        filings, paths = filing_run(state["ticker"])
        return {**state, "filings": filings, "status": "filings_complete"}
    except Exception as e:
        errors = state.get("errors") or []
        return {**state, "errors": errors + [f"FilingAgent: {e}"],
                "status": "filing_failed"}


def extraction_node(state: FinancialState) -> FinancialState:
    print("\n🔵 [Node 2/4] Financial Extraction Agent running...")
    try:
        financials = extraction_run(state["ticker"])
        return {**state, "financials": financials, "status": "extraction_complete"}
    except Exception as e:
        errors = state.get("errors") or []
        return {**state, "errors": errors + [f"ExtractionAgent: {e}"],
                "status": "extraction_failed"}


def valuation_node(state: FinancialState) -> FinancialState:
    print("\n🔵 [Node 3/4] Valuation Agent running...")
    try:
        valuation = valuation_run(state["ticker"])
        return {**state, "valuation": valuation, "status": "valuation_complete"}
    except Exception as e:
        errors = state.get("errors") or []
        return {**state, "errors": errors + [f"ValuationAgent: {e}"],
                "status": "valuation_failed"}


def news_node(state: FinancialState) -> FinancialState:
    print("\n🔵 [Node 4/4] News Research Agent running...")
    try:
        news = news_run(state["ticker"])
        return {**state, "news": news, "status": "news_complete"}
    except Exception as e:
        errors = state.get("errors") or []
        return {**state, "errors": errors + [f"NewsAgent: {e}"],
                "status": "news_failed"}

def rag_node(state: FinancialState) -> FinancialState:
    print("\n🔵 [Node 4/5] RAG Agent running...")
    try:
        rag_results = rag_run(state["ticker"])
        return {**state, "rag": rag_results, "status": "rag_complete"}
    except Exception as e:
        errors = state.get("errors") or []
        return {**state, "errors": errors + [f"RAGAgent: {e}"],
                "status": "rag_failed"}

def summary_node(state: FinancialState) -> FinancialState:
    """Final node — prints the complete investment summary."""
    ticker = state["ticker"]

    print(f"\n{'='*60}")
    print(f"  FINAL INVESTMENT SUMMARY — {ticker}")
    print(f"{'='*60}")

    # Financials summary
    if state.get("financials"):
        m = state["financials"]["metrics"]
        r = state["financials"]["ratios"]
        print(f"\n  📊 FINANCIALS (FY2025)")
        print(f"     Revenue:         {m['Revenue'][0]['formatted']}")
        print(f"     Net Income:      {m['NetIncome'][0]['formatted']}")
        print(f"     EPS (Diluted):   {m['EPS_Diluted'][0]['formatted']}")
        print(f"     Net Margin:      {r.get('NetProfitMargin','N/A')}")
        print(f"     ROE:             {r.get('ROE','N/A')}")

    # Valuation summary
    if state.get("valuation"):
        v   = state["valuation"]
        rec = v["recommendation"]
        dcf = v["dcf"]
        print(f"\n  💰 VALUATION")
        print(f"     Current Price:   ${v['market']['current_price']:,.2f}")
        print(f"     DCF Value:       ${dcf['intrinsic_value']:,.2f}  ({dcf['upside_downside']:+.1f}%)")
        print(f"     Analyst Target:  ${rec['analyst_target']:,.2f}  ({rec['analyst_upside']:+.1f}%)")
        print(f"     Recommendation:  {rec['color']} {rec['recommendation']}  "
              f"(Confidence: {rec['confidence']})")

    # News summary
    if state.get("news"):
        s = state["news"]["sentiment"]
        print(f"\n  📰 NEWS SENTIMENT")
        print(f"     Overall:         {s['emoji']} {s['overall']}  (score: {s['score']:+.3f})")
        print(f"     Articles:        {s['total']} analyzed")
        print(f"     Breakdown:       🟢{s['breakdown']['bullish']} bullish  "
              f"🟡{s['breakdown']['neutral']} neutral  "
              f"🔴{s['breakdown']['bearish']} bearish")
    # RAG insights
    if state.get("rag"):
        answers = state["rag"].get("questions", {})
        print(f"\n  📄 RAG INSIGHTS FROM 10-K FILINGS")
        for i, (q, a) in enumerate(list(answers.items())[:2], 1):
            short_q = q.replace(f"{state['ticker']} ", "").replace("What was ", "").replace("What are ", "")
            print(f"  {i}. {short_q[:50]}...")
            print(f"     {a[:150]}...")    

    # Errors if any
    if state.get("errors"):
        print(f"\n  ⚠️  ERRORS: {state['errors']}")

    print(f"\n{'='*60}")
    print(f"  Pipeline complete. All agents finished successfully.")
    print(f"{'='*60}\n")

    return {**state, "status": "complete"}


# ─────────────────────────────────────────────
#  CONDITIONAL EDGE — skip valuation if extraction failed
# ─────────────────────────────────────────────
def should_run_valuation(state: FinancialState) -> str:
    if state.get("status") == "extraction_failed":
        print("  ⚠ Extraction failed — skipping valuation")
        return "skip_valuation"
    return "run_valuation"


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

    graph.add_edge("valuation_agent", "news_agent")
    graph.add_edge("news_agent",      "rag_agent")
    graph.add_edge("rag_agent",       "summary_agent")
    graph.add_edge("summary_agent",   END)

    return graph.compile()
# ─────────────────────────────────────────────
#  RUN
# ─────────────────────────────────────────────
def run_pipeline(ticker: str = "AAPL") -> dict:
    print(f"\n{'='*60}")
    print(f"  🚀 AGENTIC FINANCIAL INTELLIGENCE PLATFORM")
    print(f"  Starting multi-agent pipeline for: {ticker}")
    print(f"{'='*60}")

    graph = build_graph()

    initial_state: FinancialState = {
        "ticker":     ticker,
        "filings":    None,
        "financials": None,
        "valuation":  None,
        "news":       None,
        "rag":        None,
        "errors":     [],
        "status":     "starting"
    }

    final_state = graph.invoke(initial_state)
    return final_state


if __name__ == "__main__":
    run_pipeline("AAPL")