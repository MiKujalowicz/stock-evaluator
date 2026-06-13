import logging
from typing import Dict, Any, List
import yfinance as yf
import pandas as pd

logger = logging.getLogger(__name__)

# Standard mock database of stock details to use if offline or yfinance fails
MOCK_DATABASE: Dict[str, Dict[str, Any]] = {
    "AAPL": {
        "ticker": "AAPL",
        "name": "Apple Inc.",
        "price": 178.50,
        "market_cap": 2800000000000,
        "pe_ratio": 28.5,
        "forward_pe": 26.2,
        "eps": 6.25,
        "peg_ratio": 2.1,
        "fifty_two_week_high": 199.62,
        "fifty_two_week_low": 164.08,
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "summary": "Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories worldwide. The company is known for its iPhone, iPad, Mac, and services like the App Store and Apple Pay."
    },
    "TSLA": {
        "ticker": "TSLA",
        "name": "Tesla, Inc.",
        "price": 175.20,
        "market_cap": 550000000000,
        "pe_ratio": 48.3,
        "forward_pe": 40.5,
        "eps": 3.62,
        "peg_ratio": 3.4,
        "fifty_two_week_high": 299.29,
        "fifty_two_week_low": 138.80,
        "sector": "Consumer Cyclical",
        "industry": "Auto Manufacturers",
        "summary": "Tesla, Inc. designs, develops, manufactures, leases, and sells electric vehicles, and energy generation and storage systems in the United States, China, and internationally. It operates in two segments, Automotive, and Energy Generation and Storage."
    },
    "NVDA": {
        "ticker": "NVDA",
        "name": "NVIDIA Corporation",
        "price": 900.30,
        "market_cap": 2250000000000,
        "pe_ratio": 72.8,
        "forward_pe": 32.5,
        "eps": 12.36,
        "peg_ratio": 1.2,
        "fifty_two_week_high": 974.00,
        "fifty_two_week_low": 280.12,
        "sector": "Technology",
        "industry": "Semiconductors",
        "summary": "NVIDIA Corporation focuses on personal computer graphics, graphics processing units, and also on artificial intelligence solutions. It operates through two segments: Graphics and Compute & Networking."
    },
    "MSFT": {
        "ticker": "MSFT",
        "name": "Microsoft Corporation",
        "price": 415.50,
        "market_cap": 3100000000000,
        "pe_ratio": 36.1,
        "forward_pe": 31.8,
        "eps": 11.51,
        "peg_ratio": 2.4,
        "fifty_two_week_high": 430.82,
        "fifty_two_week_low": 315.18,
        "sector": "Technology",
        "industry": "Software - Infrastructure",
        "summary": "Microsoft Corporation develops and supports software, services, devices, and solutions worldwide. The company operates in three segments: Productivity and Business Processes, Intelligent Cloud, and More Personal Computing."
    },
    "AMZN": {
        "ticker": "AMZN",
        "name": "Amazon.com, Inc.",
        "price": 180.20,
        "market_cap": 1870000000000,
        "pe_ratio": 41.5,
        "forward_pe": 33.2,
        "eps": 4.34,
        "peg_ratio": 1.5,
        "fifty_two_week_high": 189.77,
        "fifty_two_week_low": 114.21,
        "sector": "Consumer Cyclical",
        "industry": "Internet Retail",
        "summary": "Amazon.com, Inc. engages in the retail sale of consumer products and subscriptions in North America and internationally. It operates through three segments: North America, International, and Amazon Web Services (AWS)."
    }
}

def fetch_fundamentals(ticker: str) -> Dict[str, Any]:
    """
    Fetches fundamental financial information for a given stock ticker.
    Falls back to mock data if ticker is invalid or API fails.
    """
    ticker_upper = ticker.strip().upper()
    logger.info(f"Fetching fundamentals for {ticker_upper}")
    
    try:
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
        
    except Exception as e:
        logger.warning(f"Error fetching real fundamentals for {ticker_upper}: {e}. Falling back to mock data.")
        # Try to return known mock data, or generate dynamic mock data for other tickers
        if ticker_upper in MOCK_DATABASE:
            return MOCK_DATABASE[ticker_upper]
        else:
            return {
                "ticker": ticker_upper,
                "name": f"{ticker_upper} Corp (Mock)",
                "price": 150.00,
                "market_cap": 100000000000,
                "pe_ratio": 22.5,
                "forward_pe": 18.2,
                "eps": 6.67,
                "peg_ratio": 1.5,
                "fifty_two_week_high": 185.00,
                "fifty_two_week_low": 120.00,
                "sector": "Technology",
                "industry": "Information Services",
                "summary": f"This is mock profile data for {ticker_upper} Corporation. The server was unable to retrieve live financial attributes from the external provider."
            }

def fetch_chart_data(ticker: str) -> List[Dict[str, Any]]:
    """
    Fetches historical stock close prices for the past 30 days.
    """
    ticker_upper = ticker.strip().upper()
    try:
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
        
    except Exception as e:
        logger.warning(f"Error fetching real history for {ticker_upper}: {e}. Generating mock history.")
        # Generate generic mock historical data
        import random
        base_price = MOCK_DATABASE.get(ticker_upper, {}).get("price", 150.0)
        chart = []
        from datetime import datetime, timedelta
        now = datetime.now()
        
        for i in range(30, 0, -1):
            date_str = (now - timedelta(days=i)).strftime("%Y-%m-%d")
            # Random walk around the base price
            base_price += random.uniform(-3, 3)
            chart.append({
                "date": date_str,
                "close": round(base_price, 2)
            })
        return chart
