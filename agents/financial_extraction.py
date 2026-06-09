import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import requests
import time
from pathlib import Path
from config import SEC_USER_AGENT, CACHE_DIR
from agents.filing_retrieval import get_cik

HEADERS = {"User-Agent": SEC_USER_AGENT}

# Key financial metrics we want to extract
# Some companies use different XBRL tag names for the same concept
METRICS = {
    "Revenue": [
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet"
    ],
    "NetIncome": [
        "NetIncomeLoss",
        "ProfitLoss"
    ],
    "OperatingIncome": [
        "OperatingIncomeLoss"
    ],
    "EPS_Basic": [
        "EarningsPerShareBasic"
    ],
    "EPS_Diluted": [
        "EarningsPerShareDiluted"
    ],
    "TotalAssets": [
        "Assets"
    ],
    "TotalLiabilities": [
        "Liabilities"
    ],
    "StockholdersEquity": [
        "StockholdersEquity",
        "StockholdersEquityAttributableToParent"
    ],
    "CashAndEquivalents": [
        "CashAndCashEquivalentsAtCarryingValue"
    ],
    "OperatingCashFlow": [
        "NetCashProvidedByUsedInOperatingActivities"
    ]
}


def get_company_facts(ticker: str) -> dict:
    """Fetch all XBRL financial facts for a company from SEC."""
    cache_file = CACHE_DIR / f"{ticker}_facts.json"

    if cache_file.exists():
        print(f"Loading {ticker} financial facts from cache...")
        return json.loads(cache_file.read_text())

    print(f"Fetching {ticker} financial facts from SEC EDGAR...")
    cik = get_cik(ticker)
    time.sleep(0.15)

    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    facts = r.json()

    cache_file.write_text(json.dumps(facts))
    print(f"Saved facts to cache.")
    return facts


def extract_annual_values(facts: dict, tags: list) -> list:
    """Try multiple XBRL tag names and return annual values."""
    gaap = facts.get("facts", {}).get("us-gaap", {})

    for tag in tags:
        if tag in gaap:
            units = gaap[tag].get("units", {})
            values = units.get("USD", units.get("shares", []))
            # Filter for annual 10-K filings only, remove duplicates
            annual = [
                v for v in values
                if v.get("form") == "10-K" and v.get("frame") is not None
            ]
            if not annual:
                # fallback — get 10-K without frame filter
                annual = [v for v in values if v.get("form") == "10-K"]
            if annual:
                return sorted(annual, key=lambda x: x["end"], reverse=True)
    return []


def format_number(value: float, metric_name: str) -> str:
    """Format large numbers into readable billions/millions."""
    if "EPS" in metric_name:
        return f"${value:.2f}"
    if abs(value) >= 1_000_000_000:
        return f"${value/1_000_000_000:.2f}B"
    if abs(value) >= 1_000_000:
        return f"${value/1_000_000:.2f}M"
    return f"${value:,.0f}"


def extract_financials(ticker: str, years: int = 5) -> dict:
    """
    Main extraction function.
    Returns a clean dict of financial metrics for the last N years.
    """
    facts = get_company_facts(ticker)
    results = {}

    print(f"\nExtracting financials for {ticker}...\n")

    for metric_name, tags in METRICS.items():
        values = extract_annual_values(facts, tags)

        if not values:
            print(f"  ✗ {metric_name:<25} — not found")
            results[metric_name] = []
            continue

        # Take the most recent N years
        recent = values[:years]
        results[metric_name] = [
            {
                "year": v["end"][:4],
                "period_end": v["end"],
                "value": v["val"],
                "formatted": format_number(v["val"], metric_name)
            }
            for v in recent
        ]

        latest = recent[0]
        print(f"  ✓ {metric_name:<25} {format_number(latest['val'], metric_name):>12}  ({latest['end'][:4]})")

    return results


def calculate_ratios(financials: dict) -> dict:
    """Calculate key financial ratios from extracted data."""
    ratios = {}

    try:
        rev   = financials["Revenue"][0]["value"]
        ni    = financials["NetIncome"][0]["value"]
        assets = financials["TotalAssets"][0]["value"]
        equity = financials["StockholdersEquity"][0]["value"]
        liab  = financials["TotalLiabilities"][0]["value"]

        ratios["NetProfitMargin"]  = f"{(ni / rev * 100):.1f}%"
        ratios["ROA"]              = f"{(ni / assets * 100):.1f}%"
        ratios["ROE"]              = f"{(ni / equity * 100):.1f}%" if equity > 0 else "N/A"
        ratios["DebtToEquity"]     = f"{(liab / equity):.2f}x" if equity > 0 else "N/A"

    except (KeyError, IndexError, ZeroDivisionError):
        pass

    return ratios


def run(ticker: str = "AAPL"):
    """Main runner for Financial Extraction Agent."""
    print(f"\n{'='*55}")
    print(f"  Financial Extraction Agent — {ticker}")
    print(f"{'='*55}\n")

    # Extract all metrics
    financials = extract_financials(ticker)

    # Calculate ratios
    ratios = calculate_ratios(financials)

    # Print ratio summary
    if ratios:
        print(f"\n--- Key Ratios (latest year) ---")
        for name, value in ratios.items():
            print(f"  {name:<25} {value:>10}")

    # Save results
    output_file = CACHE_DIR / f"{ticker}_financials.json"
    output = {"ticker": ticker, "metrics": financials, "ratios": ratios}
    output_file.write_text(json.dumps(output, indent=2))

    print(f"\n{'='*55}")
    print(f"  SUCCESS — financials saved to cache")
    print(f"  File: {output_file}")
    print(f"{'='*55}\n")

    return output


if __name__ == "__main__":
    run("AAPL")