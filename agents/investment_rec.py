import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from pathlib import Path
from openai import OpenAI
from config import OPENAI_API_KEY, CACHE_DIR


def build_investment_prompt(ticker: str, financials: dict,
                             valuation: dict, news: dict, rag: dict) -> str:
    """Build a structured prompt from all agent outputs."""

    # Extract key data
    m   = financials.get("metrics", {})
    r   = financials.get("ratios", {})
    rec = valuation.get("recommendation", {})
    dcf = valuation.get("dcf", {})
    mkt = valuation.get("market", {})
    sen = news.get("sentiment", {})

    rev = m.get("Revenue", [{}])[0].get("formatted", "N/A")
    ni  = m.get("NetIncome", [{}])[0].get("formatted", "N/A")
    eps = m.get("EPS_Diluted", [{}])[0].get("formatted", "N/A")

    # RAG insights
    rag_answers = rag.get("questions", {})
    rag_text    = "\n".join([f"- {a[:200]}" for a in list(rag_answers.values())[:3]])

    prompt = f"""You are a senior investment analyst. Based on the following data, 
write a structured investment recommendation memo for {ticker}.

FINANCIAL DATA:
- Revenue: {rev}
- Net Income: {ni}
- EPS (Diluted): {eps}
- Net Profit Margin: {r.get('NetProfitMargin', 'N/A')}
- ROE: {r.get('ROE', 'N/A')}
- Debt/Equity: {r.get('DebtToEquity', 'N/A')}

VALUATION:
- Current Price: ${mkt.get('current_price', 0):,.2f}
- DCF Intrinsic Value: ${dcf.get('intrinsic_value', 0):,.2f}
- DCF Upside/Downside: {dcf.get('upside_downside', 0):+.1f}%
- Analyst Consensus Target: ${rec.get('analyst_target', 0):,.2f}
- Model Recommendation: {rec.get('recommendation', 'N/A')}

NEWS SENTIMENT:
- Overall: {sen.get('overall', 'N/A')} (score: {sen.get('score', 0):+.3f})
- Breakdown: {sen.get('breakdown', {})}

KEY INSIGHTS FROM 10-K FILINGS:
{rag_text}

Write a professional investment memo with these exact sections:
1. EXECUTIVE SUMMARY (2-3 sentences with final recommendation)
2. INVESTMENT THESIS (3 key reasons for the recommendation)
3. FINANCIAL HIGHLIGHTS (key metrics analysis)
4. RISK FACTORS (top 3 risks from the 10-K)
5. VALUATION SUMMARY (DCF vs market price analysis)
6. FINAL RECOMMENDATION (BUY/HOLD/SELL with 12-month price target)

Keep each section concise and professional. Use actual numbers from the data provided."""

    return prompt


def generate_recommendation(ticker: str, financials: dict,
                             valuation: dict, news: dict, rag: dict) -> dict:
    """Use GPT-4o-mini to generate a structured investment memo."""
    client = OpenAI(api_key=OPENAI_API_KEY)

    prompt = build_investment_prompt(ticker, financials, valuation, news, rag)

    print(f"  Generating investment memo with GPT-4o-mini...")
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a senior Wall Street investment analyst. "
                           "Write clear, data-driven, professional investment memos."
            },
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
        max_tokens=1500
    )

    memo_text = response.choices[0].message.content

    return {
        "ticker":     ticker,
        "memo":       memo_text,
        "model_used": "gpt-4o-mini",
        "recommendation": valuation.get("recommendation", {}).get("recommendation", "HOLD")
    }


def run(ticker: str = "AAPL") -> dict:
    """Main Investment Recommendation Agent runner."""
    print(f"\n{'='*55}")
    print(f"  Investment Recommendation Agent — {ticker}")
    print(f"{'='*55}\n")

    # Load cached data from previous agents
    fin_file = CACHE_DIR / f"{ticker}_financials.json"
    val_file = CACHE_DIR / f"{ticker}_valuation.json"
    news_file = CACHE_DIR / f"{ticker}_news.json"

    if not fin_file.exists():
        raise FileNotFoundError("Run financial_extraction.py first")
    if not val_file.exists():
        raise FileNotFoundError("Run valuation.py first")
    if not news_file.exists():
        raise FileNotFoundError("Run news_research.py first")

    financials = json.loads(fin_file.read_text())
    valuation  = json.loads(val_file.read_text())
    news       = json.loads(news_file.read_text())

    # Load RAG data if available
    rag = {"questions": {}}
    try:
        from agents.rag_agent import run as rag_run
        rag = rag_run(ticker)
    except Exception as e:
        print(f"  ⚠ RAG data not available: {e}")

    # Generate the memo
    result = generate_recommendation(ticker, financials, valuation, news, rag)

    # Print the memo
    print(f"\n{'='*55}")
    print(f"  INVESTMENT MEMO — {ticker}")
    print(f"{'='*55}")
    print(result["memo"])
    print(f"{'='*55}\n")

    # Save to cache
    out_file = CACHE_DIR / f"{ticker}_investment_memo.json"
    out_file.write_text(json.dumps(result, indent=2))

    print(f"  ✓ Memo saved to: {out_file}")
    return result


if __name__ == "__main__":
    run("AAPL")