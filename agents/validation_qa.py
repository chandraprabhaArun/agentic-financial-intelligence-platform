import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from config import CACHE_DIR


def validate_financials(financials: dict) -> list:
    """Check financial data for consistency and completeness."""
    issues = []
    m = financials.get("metrics", {})
    r = financials.get("ratios", {})

    # Check all key metrics are present
    required = ["Revenue","NetIncome","EPS_Diluted","TotalAssets",
                "TotalLiabilities","StockholdersEquity","OperatingCashFlow"]
    for metric in required:
        if not m.get(metric) or len(m[metric]) == 0:
            issues.append(f"MISSING: {metric} not found in financial data")

    # Check Assets = Liabilities + Equity (balance sheet equation)
    try:
        assets  = m["TotalAssets"][0]["value"]
        liab    = m["TotalLiabilities"][0]["value"]
        equity  = m["StockholdersEquity"][0]["value"]
        balance = abs(assets - (liab + equity))
        pct     = balance / assets * 100
        if pct > 5:
            issues.append(
                f"BALANCE SHEET: Assets ({assets/1e9:.1f}B) ≠ "
                f"Liabilities ({liab/1e9:.1f}B) + Equity ({equity/1e9:.1f}B) "
                f"— gap: {pct:.1f}%"
            )
        else:
            issues.append(f"✓ Balance sheet checks out (gap: {pct:.1f}%)")
    except (KeyError, IndexError, ZeroDivisionError) as e:
        issues.append(f"BALANCE SHEET: Could not verify — {e}")

    # Check net margin is reasonable (0-100%)
    try:
        margin = float(r.get("NetProfitMargin","0%").replace("%",""))
        if margin < 0:
            issues.append(f"WARNING: Negative net margin ({margin:.1f}%) — company losing money")
        elif margin > 50:
            issues.append(f"WARNING: Very high net margin ({margin:.1f}%) — verify data")
        else:
            issues.append(f"✓ Net margin {margin:.1f}% is reasonable")
    except ValueError:
        issues.append("WARNING: Could not parse net margin")

    return issues


def validate_valuation(valuation: dict, financials: dict) -> list:
    """Cross-check valuation data against financials."""
    issues = []
    mkt = valuation.get("market", {})
    dcf = valuation.get("dcf", {})
    m   = financials.get("metrics", {})

    # Check current price is realistic
    price = mkt.get("current_price", 0)
    if price <= 0:
        issues.append("ERROR: Current price is zero or negative")
    elif price > 10000:
        issues.append(f"WARNING: Price ${price:,.2f} seems very high — verify ticker")
    else:
        issues.append(f"✓ Current price ${price:,.2f} looks valid")

    # Check DCF used correct base FCF
    dcf_base = dcf.get("fcf_base", 0)
    try:
        ocf = m["OperatingCashFlow"][0]["value"]
        diff_pct = abs(dcf_base - ocf) / ocf * 100
        if diff_pct < 1:
            issues.append(f"✓ DCF base FCF matches operating cash flow ({dcf_base/1e9:.1f}B)")
        else:
            issues.append(f"WARNING: DCF FCF ({dcf_base/1e9:.1f}B) differs from OCF ({ocf/1e9:.1f}B)")
    except (KeyError, IndexError, ZeroDivisionError):
        issues.append("WARNING: Could not verify DCF base FCF")

    # Check analyst target is within reasonable range of current price
    analyst_target = valuation.get("recommendation", {}).get("analyst_target", 0)
    if price > 0 and analyst_target > 0:
        diff = abs(analyst_target - price) / price * 100
        if diff > 100:
            issues.append(f"WARNING: Analyst target ${analyst_target:,.2f} is >100% from current price")
        else:
            issues.append(f"✓ Analyst target ${analyst_target:,.2f} is within reasonable range")

    return issues


def validate_news(news: dict) -> list:
    """Validate news sentiment data."""
    issues = []
    sen       = news.get("sentiment", {})
    articles  = news.get("articles", [])

    if len(articles) == 0:
        issues.append("WARNING: No news articles found")
    elif len(articles) < 3:
        issues.append(f"WARNING: Only {len(articles)} articles — limited sentiment signal")
    else:
        issues.append(f"✓ {len(articles)} news articles analyzed")

    score = sen.get("score", 0)
    if -1 <= score <= 1:
        issues.append(f"✓ Sentiment score {score:+.3f} is within valid range")
    else:
        issues.append(f"ERROR: Sentiment score {score} is out of range [-1, 1]")

    return issues


def validate_memo(memo: dict) -> list:
    """Validate the investment memo for completeness."""
    issues  = []
    text    = memo.get("memo", "")
    required_sections = [
        "EXECUTIVE SUMMARY",
        "INVESTMENT THESIS",
        "FINANCIAL HIGHLIGHTS",
        "RISK FACTORS",
        "VALUATION SUMMARY",
        "FINAL RECOMMENDATION"
    ]

    for section in required_sections:
        if section in text.upper():
            issues.append(f"✓ Section present: {section}")
        else:
            issues.append(f"MISSING: Section not found: {section}")

    word_count = len(text.split())
    if word_count < 200:
        issues.append(f"WARNING: Memo is very short ({word_count} words)")
    else:
        issues.append(f"✓ Memo length: {word_count} words")

    return issues


def run(ticker: str = "AAPL") -> dict:
    """Main Validation & QA Agent runner."""
    print(f"\n{'='*55}")
    print(f"  Validation & QA Agent — {ticker}")
    print(f"{'='*55}\n")

    # Load all cached outputs
    fin_file  = CACHE_DIR / f"{ticker}_financials.json"
    val_file  = CACHE_DIR / f"{ticker}_valuation.json"
    news_file = CACHE_DIR / f"{ticker}_news.json"
    memo_file = CACHE_DIR / f"{ticker}_investment_memo.json"

    financials = json.loads(fin_file.read_text()) if fin_file.exists() else {}
    valuation  = json.loads(val_file.read_text()) if val_file.exists() else {}
    news       = json.loads(news_file.read_text()) if news_file.exists() else {}
    memo       = json.loads(memo_file.read_text()) if memo_file.exists() else {}

    all_issues = {}
    error_count   = 0
    warning_count = 0
    pass_count    = 0

    # Run all validations
    checks = {
        "Financial Data":   validate_financials(financials),
        "Valuation Model":  validate_valuation(valuation, financials),
        "News Sentiment":   validate_news(news),
        "Investment Memo":  validate_memo(memo),
    }

    for category, issues in checks.items():
        print(f"  [{category}]")
        for issue in issues:
            print(f"    {issue}")
            if issue.startswith("✓"):
                pass_count += 1
            elif "ERROR" in issue or "MISSING" in issue:
                error_count += 1
            elif "WARNING" in issue:
                warning_count += 1
        print()
        all_issues[category] = issues

    # Overall status
    if error_count == 0 and warning_count == 0:
        status = "PASSED"
        emoji  = "✅"
    elif error_count == 0:
        status = "PASSED WITH WARNINGS"
        emoji  = "⚠️"
    else:
        status = "FAILED"
        emoji  = "❌"

    print(f"{'='*55}")
    print(f"  QA STATUS: {emoji} {status}")
    print(f"  ✓ Passed:   {pass_count}")
    print(f"  ⚠ Warnings: {warning_count}")
    print(f"  ✗ Errors:   {error_count}")
    print(f"{'='*55}\n")

    result = {
        "ticker":        ticker,
        "status":        status,
        "pass_count":    pass_count,
        "warning_count": warning_count,
        "error_count":   error_count,
        "checks":        all_issues
    }

    out_file = CACHE_DIR / f"{ticker}_qa_report.json"
    out_file.write_text(json.dumps(result, indent=2))
    print(f"  ✓ QA report saved: {out_file}")

    return result


if __name__ == "__main__":
    run("AAPL")