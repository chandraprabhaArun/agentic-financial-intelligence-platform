import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import json
import time
from pathlib import Path
from config import SEC_USER_AGENT, FILINGS_DIR, CACHE_DIR

HEADERS = {"User-Agent": SEC_USER_AGENT}


def get_cik(ticker: str) -> str:
    """Convert stock ticker to SEC CIK number."""
    cache_file = CACHE_DIR / "company_tickers.json"

    # Use cached ticker list if available
    if cache_file.exists():
        tickers = json.loads(cache_file.read_text())
    else:
        print("Downloading SEC ticker list...")
        r = requests.get(
            "https://www.sec.gov/files/company_tickers.json",
            headers=HEADERS
        )
        tickers = r.json()
        cache_file.write_text(json.dumps(tickers))

    for entry in tickers.values():
        if entry["ticker"].upper() == ticker.upper():
            return str(entry["cik_str"]).zfill(10)

    raise ValueError(f"Ticker '{ticker}' not found in SEC database")


def get_recent_filings(ticker: str, form_type: str = "10-K", n: int = 3) -> list:
    """Get list of recent SEC filings for a ticker."""
    cache_file = CACHE_DIR / f"{ticker}_{form_type}_filings.json"

    # Return cached result if available
    if cache_file.exists():
        print(f"Loading {ticker} {form_type} filings from cache...")
        return json.loads(cache_file.read_text())

    print(f"Fetching {ticker} {form_type} filings from SEC EDGAR...")
    cik = get_cik(ticker)

    time.sleep(0.15)  # Respect SEC rate limit (max 10 req/sec)
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    data = requests.get(url, headers=HEADERS).json()

    filings = []
    recent = data["filings"]["recent"]

    for i, form in enumerate(recent["form"]):
        if form == form_type:
            accn = recent["accessionNumber"][i].replace("-", "")
            filing = {
                "ticker":   ticker,
                "form":     form_type,
                "date":     recent["filingDate"][i],
                "accession": accn,
                "url": (
                    f"https://www.sec.gov/Archives/edgar/data/"
                    f"{int(cik)}/{accn}/{recent['primaryDocument'][i]}"
                )
            }
            filings.append(filing)
            if len(filings) == n:
                break

    # Save to cache
    cache_file.write_text(json.dumps(filings, indent=2))
    print(f"Saved {len(filings)} filings to cache.")
    return filings


def download_filing(filing: dict) -> Path:
    """Download the actual filing HTML document."""
    fname = f"{filing['ticker']}_{filing['form']}_{filing['date']}.html"
    fpath = FILINGS_DIR / filing["ticker"]
    fpath.mkdir(parents=True, exist_ok=True)
    fpath = fpath / fname

    if fpath.exists():
        print(f"Already downloaded: {fname}")
        return fpath

    print(f"Downloading: {fname} ...")
    time.sleep(0.15)
    r = requests.get(filing["url"], headers=HEADERS)
    fpath.write_text(r.text, encoding="utf-8")
    print(f"Saved to: {fpath}")
    return fpath


def run(ticker: str = "AAPL"):
    """Main function — fetch and download filings for a ticker."""
    print(f"\n{'='*50}")
    print(f"  Filing Retrieval Agent — {ticker}")
    print(f"{'='*50}\n")

    # Get filing metadata
    filings = get_recent_filings(ticker, form_type="10-K", n=3)

    print(f"\nFound {len(filings)} filings:\n")
    for f in filings:
        print(f"  ✓ {f['form']} | {f['date']} | {f['url'][:60]}...")

    # Download the actual documents
    print(f"\nDownloading filing documents...")
    paths = []
    for f in filings:
        path = download_filing(f)
        paths.append(path)

    print(f"\n{'='*50}")
    print(f"  SUCCESS — {len(paths)} filings ready for RAG pipeline")
    print(f"  Saved in: {FILINGS_DIR / ticker}")
    print(f"{'='*50}\n")

    return filings, paths


if __name__ == "__main__":
    run("AAPL")