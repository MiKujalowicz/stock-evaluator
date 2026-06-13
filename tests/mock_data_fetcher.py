from typing import Dict, Any, List
import random
from datetime import datetime, timedelta

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

def fetch_fundamentals_mock(ticker: str) -> Dict[str, Any]:
    """
    Mock fetch_fundamentals returning predefined data or standard mock structure.
    Raises ValueError for special invalid tickers if needed.
    """
    ticker_upper = ticker.strip().upper()
    if ticker_upper == "INVALID":
        raise ValueError(f"No info returned for ticker {ticker_upper}")
        
    if ticker_upper in MOCK_DATABASE:
        return MOCK_DATABASE[ticker_upper].copy()
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

def fetch_chart_data_mock(ticker: str) -> List[Dict[str, Any]]:
    """
    Mock fetch_chart_data returning generic 30-day stock close history.
    """
    ticker_upper = ticker.strip().upper()
    if ticker_upper == "INVALID":
        raise ValueError(f"No history returned for {ticker_upper}")
        
    base_price = MOCK_DATABASE.get(ticker_upper, {}).get("price", 150.0)
    chart = []
    now = datetime.now()
    
    # Use deterministic random generation for tests based on ticker
    rng = random.Random(hash(ticker_upper))
    
    for i in range(30, 0, -1):
        date_str = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        base_price += rng.uniform(-3, 3)
        chart.append({
            "date": date_str,
            "close": round(base_price, 2)
        })
    return chart
