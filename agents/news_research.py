import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import requests
import time
from datetime import datetime, timedelta
from pathlib import Path
from config import ALPHA_VANTAGE_KEY, CACHE_DIR

HEADERS = {"User-Agent": "FinancialAgent dev@example.com"}


def get_news_alphavantage(ticker: str, limit: int = 10) -> list:
    """Fetch news with sentiment scores from Alpha Vantage."""
    cache_file = CACHE_DIR / f"{ticker}_news_av.json"

    if cache_file.exists():
        age_hours = (time.time() - cache_file.stat().st_mtime) / 3600
        if age_hours < 6:
            print(f"Loading {ticker} news from cache...")
            return json.loads(cache_file.read_text())

    print(f"Fetching {ticker} news from Alpha Vantage...")

    if not ALPHA_VANTAGE_KEY or ALPHA_VANTAGE_KEY == "your-alpha-vantage-key-here":
        print("  ⚠ Alpha Vantage key not set — using demo news data")
        return get_demo_news(ticker)

    url = "https://www.alphavantage.co/query"
    params = {
        "function":  "NEWS_SENTIMENT",
        "tickers":   ticker,
        "limit":     limit,
        "apikey":    ALPHA_VANTAGE_KEY
    }

    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()

        if "feed" not in data:
            print(f"  ⚠ API limit reached or invalid key — using demo data")
            return get_demo_news(ticker)

        articles = []
        for item in data["feed"][:limit]:
            # Find sentiment score for this specific ticker
            ticker_sentiment = next(
                (t for t in item.get("ticker_sentiment", [])
                 if t["ticker"] == ticker),
                {}
            )
            articles.append({
                "title":          item.get("title", ""),
                "summary":        item.get("summary", "")[:200],
                "url":            item.get("url", ""),
                "published":      item.get("time_published", "")[:8],
                "source":         item.get("source", ""),
                "overall_sentiment": item.get("overall_sentiment_label", "Neutral"),
                "sentiment_score":   float(item.get("overall_sentiment_score", 0)),
                "ticker_sentiment":  ticker_sentiment.get("ticker_sentiment_label", "Neutral"),
                "ticker_relevance":  float(ticker_sentiment.get("relevance_score", 0))
            })

        cache_file.write_text(json.dumps(articles, indent=2))
        return articles

    except Exception as e:
        print(f"  ⚠ Error fetching news: {e} — using demo data")
        return get_demo_news(ticker)


def get_demo_news(ticker: str) -> list:
    """Demo news data for when API key is not available."""
    return [
        {
            "title": f"{ticker} Reports Strong Quarterly Earnings",
            "summary": f"{ticker} beat analyst estimates with strong revenue growth driven by services segment.",
            "url": "https://example.com/news/1",
            "published": "20250601",
            "source": "Financial Times",
            "overall_sentiment": "Bullish",
            "sentiment_score": 0.45,
            "ticker_sentiment": "Bullish",
            "ticker_relevance": 0.95
        },
        {
            "title": f"{ticker} Faces Regulatory Scrutiny in EU Markets",
            "summary": f"European regulators are investigating {ticker}'s market practices.",
            "url": "https://example.com/news/2",
            "published": "20250528",
            "source": "Reuters",
            "overall_sentiment": "Bearish",
            "sentiment_score": -0.32,
            "ticker_sentiment": "Bearish",
            "ticker_relevance": 0.88
        },
        {
            "title": f"{ticker} Announces New Product Line for 2025",
            "summary": f"{ticker} unveiled its next generation product lineup at its annual developer conference.",
            "url": "https://example.com/news/3",
            "published": "20250520",
            "source": "Bloomberg",
            "overall_sentiment": "Bullish",
            "sentiment_score": 0.38,
            "ticker_sentiment": "Bullish",
            "ticker_relevance": 0.92
        },
        {
            "title": f"Analysts Raise Price Target for {ticker}",
            "summary": f"Multiple Wall Street firms raised their price targets citing strong fundamentals.",
            "url": "https://example.com/news/4",
            "published": "20250515",
            "source": "WSJ",
            "overall_sentiment": "Bullish",
            "sentiment_score": 0.52,
            "ticker_sentiment": "Bullish",
            "ticker_relevance": 0.85
        },
        {
            "title": f"{ticker} Supply Chain Concerns Weigh on Outlook",
            "summary": f"Supply constraints may impact {ticker}'s production targets for next quarter.",
            "url": "https://example.com/news/5",
            "published": "20250510",
            "source": "CNBC",
            "overall_sentiment": "Bearish",
            "sentiment_score": -0.28,
            "ticker_sentiment": "Bearish",
            "ticker_relevance": 0.79
        }
    ]


def analyze_sentiment(articles: list) -> dict:
    """Aggregate sentiment analysis across all articles."""
    if not articles:
        return {"overall": "Neutral", "score": 0, "breakdown": {}}

    scores      = [a["sentiment_score"] for a in articles]
    avg_score   = sum(scores) / len(scores)

    bullish  = sum(1 for a in articles if a["sentiment_score"] > 0.15)
    bearish  = sum(1 for a in articles if a["sentiment_score"] < -0.15)
    neutral  = len(articles) - bullish - bearish

    if avg_score > 0.15:
        overall = "Bullish"
        emoji   = "🟢"
    elif avg_score < -0.15:
        overall = "Bearish"
        emoji   = "🔴"
    else:
        overall = "Neutral"
        emoji   = "🟡"

    return {
        "overall":      overall,
        "emoji":        emoji,
        "score":        round(avg_score, 3),
        "total":        len(articles),
        "breakdown": {
            "bullish":  bullish,
            "bearish":  bearish,
            "neutral":  neutral
        },
        "top_positive": max(articles, key=lambda x: x["sentiment_score"])["title"],
        "top_negative": min(articles, key=lambda x: x["sentiment_score"])["title"]
    }


def run(ticker: str = "AAPL"):
    """Main News Research Agent runner."""
    print(f"\n{'='*55}")
    print(f"  News Research Agent — {ticker}")
    print(f"{'='*55}\n")

    # Fetch news articles
    articles = get_news_alphavantage(ticker)

    # Analyze sentiment
    sentiment = analyze_sentiment(articles)

    # Print results
    print(f"  Articles analyzed:  {sentiment['total']}")
    print(f"  Overall Sentiment:  {sentiment['emoji']}  {sentiment['overall']}")
    print(f"  Sentiment Score:    {sentiment['score']:+.3f}  (-1 bearish → +1 bullish)")
    print(f"  Breakdown:          🟢 {sentiment['breakdown']['bullish']} bullish  |  "
          f"🟡 {sentiment['breakdown']['neutral']} neutral  |  "
          f"🔴 {sentiment['breakdown']['bearish']} bearish")

    print(f"\n  Top Positive: {sentiment['top_positive'][:65]}...")
    print(f"  Top Negative: {sentiment['top_negative'][:65]}...")

    print(f"\n  Recent Headlines:")
    for i, a in enumerate(articles[:5], 1):
        score = a['sentiment_score']
        icon  = "🟢" if score > 0.15 else "🔴" if score < -0.15 else "🟡"
        print(f"  {i}. {icon} [{a['published']}] {a['title'][:55]}...")

    # Save results
    output = {
        "ticker":    ticker,
        "sentiment": sentiment,
        "articles":  articles
    }
    out_file = CACHE_DIR / f"{ticker}_news.json"
    out_file.write_text(json.dumps(output, indent=2))

    print(f"\n{'='*55}")
    print(f"  SUCCESS — news analysis saved")
    print(f"  File: {out_file}")
    print(f"{'='*55}\n")

    return output


if __name__ == "__main__":
    run("AAPL")