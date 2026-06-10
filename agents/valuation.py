import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import yfinance as yf
from pathlib import Path
from config import CACHE_DIR
from agents.financial_extraction import run as extract_financials


def get_market_data(ticker: str) -> dict:
    """Fetch current market data using yfinance."""
    print(f"Fetching live market data for {ticker}...")
    stock = yf.Ticker(ticker)
    info  = stock.info

    return {
        "current_price":    info.get("currentPrice") or info.get("regularMarketPrice", 0),
        "market_cap":       info.get("marketCap", 0),
        "pe_ratio":         info.get("trailingPE", 0),
        "forward_pe":       info.get("forwardPE", 0),
        "pb_ratio":         info.get("priceToBook", 0),
        "ps_ratio":         info.get("priceToSalesTrailing12Months", 0),
        "beta":             info.get("beta", 1.0),
        "dividend_yield":   info.get("dividendYield", 0),
        "52w_high":         info.get("fiftyTwoWeekHigh", 0),
        "52w_low":          info.get("fiftyTwoWeekLow", 0),
        "analyst_target":   info.get("targetMeanPrice", 0),
        "shares_outstanding": info.get("sharesOutstanding", 0),
    }


def dcf_valuation(financials: dict, market: dict, ticker: str) -> dict:
    """
    Discounted Cash Flow valuation.
    Uses operating cash flow as base, projects 5 years,
    then calculates terminal value.
    """
    print("\nRunning DCF valuation...")

    # Base inputs
    try:
        fcf         = financials["metrics"]["OperatingCashFlow"][0]["value"]
        revenue     = financials["metrics"]["Revenue"][0]["value"]
        net_income  = financials["metrics"]["NetIncome"][0]["value"]
    except (KeyError, IndexError):
        return {"error": "Insufficient data for DCF"}

    # DCF assumptions
    growth_rate_5y  = 0.08    # 8% annual growth for years 1-5
    terminal_growth = 0.03    # 3% perpetual growth rate
    wacc            = 0.09    # 9% discount rate (weighted avg cost of capital)
    shares          = market.get("shares_outstanding", 1)

    # Project free cash flows for 5 years
    projected_fcf = []
    cf = fcf
    for year in range(1, 6):
        cf = cf * (1 + growth_rate_5y)
        pv = cf / ((1 + wacc) ** year)   # present value
        projected_fcf.append({
            "year": f"Year {year}",
            "fcf":  cf,
            "pv":   pv
        })

    # Terminal value (Gordon Growth Model)
    terminal_fcf   = projected_fcf[-1]["fcf"] * (1 + terminal_growth)
    terminal_value = terminal_fcf / (wacc - terminal_growth)
    terminal_pv    = terminal_value / ((1 + wacc) ** 5)

    # Intrinsic value
    total_pv          = sum(p["pv"] for p in projected_fcf) + terminal_pv
    cash              = financials["metrics"]["CashAndEquivalents"][0]["value"]
    liabilities       = financials["metrics"]["TotalLiabilities"][0]["value"]
    equity_value      = total_pv + cash - liabilities
    intrinsic_value   = equity_value / shares if shares > 0 else 0

    current_price     = market.get("current_price", 0)
    upside            = ((intrinsic_value - current_price) / current_price * 100) if current_price > 0 else 0

    return {
        "model":            "DCF",
        "fcf_base":         fcf,
        "growth_rate":      f"{growth_rate_5y*100}%",
        "wacc":             f"{wacc*100}%",
        "terminal_growth":  f"{terminal_growth*100}%",
        "projected_fcf":    projected_fcf,
        "terminal_value":   terminal_value,
        "total_pv":         total_pv,
        "intrinsic_value":  round(intrinsic_value, 2),
        "current_price":    current_price,
        "upside_downside":  round(upside, 1),
        "margin_of_safety": round(upside * -1, 1) if upside < 0 else 0
    }


def comparable_valuation(financials: dict, market: dict) -> dict:
    """
    Comparable company analysis using industry average multiples.
    Uses sector averages for tech/consumer electronics.
    """
    print("Running comparable company valuation...")

    try:
        revenue    = financials["metrics"]["Revenue"][0]["value"]
        net_income = financials["metrics"]["NetIncome"][0]["value"]
        eps        = financials["metrics"]["EPS_Diluted"][0]["value"]
    except (KeyError, IndexError):
        return {"error": "Insufficient data"}

    # Tech sector average multiples (conservative estimates)
    sector_pe  = 28.0
    sector_ps  = 6.5
    sector_pb  = 12.0

    shares = market.get("shares_outstanding", 1)

    pe_implied  = (eps * sector_pe) if eps > 0 else 0
    ps_implied  = (revenue * sector_ps / shares) if shares > 0 else 0

    current     = market.get("current_price", 0)
    avg_implied = (pe_implied + ps_implied) / 2 if pe_implied and ps_implied else 0
    upside      = ((avg_implied - current) / current * 100) if current > 0 else 0

    return {
        "model":        "Comparable Analysis",
        "sector_pe":    sector_pe,
        "sector_ps":    sector_ps,
        "pe_implied":   round(pe_implied, 2),
        "ps_implied":   round(ps_implied, 2),
        "avg_implied":  round(avg_implied, 2),
        "current_price": current,
        "upside_downside": round(upside, 1)
    }


def generate_recommendation(dcf: dict, comps: dict, market: dict) -> dict:
    """Generate BUY / HOLD / SELL based on valuation models."""
    signals = []

    # DCF signal
    dcf_upside = dcf.get("upside_downside", 0)
    if dcf_upside > 15:
        signals.append("BUY")
    elif dcf_upside < -15:
        signals.append("SELL")
    else:
        signals.append("HOLD")

    # Comps signal
    comps_upside = comps.get("upside_downside", 0)
    if comps_upside > 15:
        signals.append("BUY")
    elif comps_upside < -15:
        signals.append("SELL")
    else:
        signals.append("HOLD")

    # Final recommendation — majority vote
    buy_count  = signals.count("BUY")
    sell_count = signals.count("SELL")

    if buy_count > sell_count:
        recommendation = "BUY"
        color = "🟢"
    elif sell_count > buy_count:
        recommendation = "SELL"
        color = "🔴"
    else:
        recommendation = "HOLD"
        color = "🟡"

    # Analyst target comparison
    analyst_target = market.get("analyst_target", 0)
    current        = market.get("current_price", 0)
    analyst_upside = ((analyst_target - current) / current * 100) if current > 0 else 0

    return {
        "recommendation":   recommendation,
        "color":            color,
        "dcf_signal":       signals[0],
        "comps_signal":     signals[1],
        "analyst_target":   analyst_target,
        "analyst_upside":   round(analyst_upside, 1),
        "confidence":       "HIGH" if buy_count + sell_count == 2 else "MEDIUM"
    }


def run(ticker: str = "AAPL"):
    """Main Valuation Agent runner."""
    print(f"\n{'='*55}")
    print(f"  Valuation Agent — {ticker}")
    print(f"{'='*55}\n")

    # Get financial data
    financials = extract_financials(ticker)

    # Get live market data
    market = get_market_data(ticker)

    current = market.get("current_price", 0)
    mcap    = market.get("market_cap", 0)
    print(f"\n  Current Price:  ${current:,.2f}")
    print(f"  Market Cap:     ${mcap/1e12:.2f}T")
    print(f"  P/E Ratio:      {market.get('pe_ratio', 'N/A')}")
    print(f"  52W High:       ${market.get('52w_high', 0):,.2f}")
    print(f"  52W Low:        ${market.get('52w_low', 0):,.2f}")

    # Run valuation models
    dcf   = dcf_valuation(financials, market, ticker)
    comps = comparable_valuation(financials, market)
    rec   = generate_recommendation(dcf, comps, market)

    # Print results
    print(f"\n--- DCF Valuation ---")
    print(f"  Intrinsic Value:   ${dcf.get('intrinsic_value', 0):,.2f}")
    print(f"  Current Price:     ${dcf.get('current_price', 0):,.2f}")
    print(f"  Upside/Downside:   {dcf.get('upside_downside', 0):+.1f}%")

    print(f"\n--- Comparable Analysis ---")
    print(f"  P/E Implied:       ${comps.get('pe_implied', 0):,.2f}")
    print(f"  P/S Implied:       ${comps.get('ps_implied', 0):,.2f}")
    print(f"  Avg Implied:       ${comps.get('avg_implied', 0):,.2f}")
    print(f"  Upside/Downside:   {comps.get('upside_downside', 0):+.1f}%")

    print(f"\n--- Final Recommendation ---")
    print(f"  {rec['color']}  {rec['recommendation']}  (Confidence: {rec['confidence']})")
    print(f"  Analyst Target:    ${rec.get('analyst_target', 0):,.2f}  ({rec.get('analyst_upside', 0):+.1f}%)")

    # Save results
    output = {
        "ticker":       ticker,
        "market":       market,
        "dcf":          dcf,
        "comparables":  comps,
        "recommendation": rec
    }
    out_file = CACHE_DIR / f"{ticker}_valuation.json"
    out_file.write_text(json.dumps(output, indent=2))

    print(f"\n{'='*55}")
    print(f"  SUCCESS — valuation saved")
    print(f"  File: {out_file}")
    print(f"{'='*55}\n")

    return output


if __name__ == "__main__":
    run("AAPL")