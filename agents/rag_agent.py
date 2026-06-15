import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import OPENAI_API_KEY
from rag.pipeline import load_existing_index, query_filings


def run(ticker: str = "AAPL") -> dict:
    print(f"\n{'='*55}")
    print(f"  RAG Agent — {ticker}")
    print(f"{'='*55}\n")

    # Standard questions asked for every analysis
    questions = [
        f"What was {ticker} total revenue and net income for the most recent fiscal year?",
        f"What are the main risk factors mentioned in {ticker} latest 10-K?",
        f"What did {ticker} say about AI, machine learning, or technology strategy?",
        f"What were the key business highlights and future outlook for {ticker}?",
    ]

    print(f"Loading RAG index for {ticker}...")
    index = load_existing_index(ticker)

    results = {}
    for q in questions:
        answer = query_filings(ticker, q, index)
        results[q] = answer

    print(f"\n{'='*55}")
    print(f"  RAG Agent complete — {len(results)} questions answered")
    print(f"{'='*55}\n")

    return {
        "ticker":    ticker,
        "questions": results
    }


if __name__ == "__main__":
    run("AAPL")