import logging
from typing import Dict, Any, List
import yfinance as yf

logger = logging.getLogger(__name__)

def fetch_fundamentals(ticker: str) -> Dict[str, Any]:
    """
    Fetches fundamental financial information for a given stock ticker.
    Raises ValueError if data is not available.
    """
    ticker_upper = ticker.strip().upper()
    logger.info(f"Fetching fundamentals for {ticker_upper}")
    
    stock = yf.Ticker(ticker_upper)
    info = stock.info
    
    # If stock info is empty or doesn't have a regularMarketPrice/currentPrice, treat as failed
    if not info or ("currentPrice" not in info and "regularMarketPrice" not in info):
        raise ValueError(f"No info returned for ticker {ticker_upper}")
        
    fundamentals = {
        "ticker": ticker_upper,
        "name": info.get("longName", f"{ticker_upper} Inc."),
        "price": info.get("currentPrice") or info.get("regularMarketPrice") or 0.0,
        "market_cap": info.get("marketCap", 0),
        "pe_ratio": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "eps": info.get("trailingEps"),
        "peg_ratio": info.get("pegRatio"),
        "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
        "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
        "sector": info.get("sector", "Unknown Sector"),
        "industry": info.get("industry", "Unknown Industry"),
        "summary": info.get("longBusinessSummary", "No company description available.")
    }
    
    # Sanity check values
    for key in ["pe_ratio", "forward_pe", "eps", "peg_ratio", "fifty_two_week_high", "fifty_two_week_low"]:
        if fundamentals[key] is not None:
            fundamentals[key] = round(float(fundamentals[key]), 2)
            
    return fundamentals

def fetch_chart_data(ticker: str) -> List[Dict[str, Any]]:
    """
    Fetches historical stock close prices for the past 30 days.
    Raises ValueError if history is not available.
    """
    ticker_upper = ticker.strip().upper()
    logger.info(f"Fetching history for {ticker_upper}")
    stock = yf.Ticker(ticker_upper)
    hist = stock.history(period="1mo")
    
    if hist.empty:
        raise ValueError(f"No history returned for {ticker_upper}")
        
    chart = []
    for date, row in hist.iterrows():
        chart.append({
            "date": date.strftime("%Y-%m-%d"),
            "close": round(float(row["Close"]), 2)
        })
    return chart
