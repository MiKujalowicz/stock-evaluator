from typing import Dict, Any
from stock_predictor.agent.state import AgentState
from stock_predictor.services.data_fetcher import fetch_fundamentals, fetch_chart_data

def fetch_data_node(state: AgentState) -> Dict[str, Any]:
    ticker = state.get("ticker", "AAPL").upper()
    logs = state.get("logs", [])
    
    logs.append(f"Starting analysis for ticker: {ticker}")
    logs.append(f"Fetching market data and fundamentals from yfinance...")
    
    fundamentals = fetch_fundamentals(ticker)
    market_data = fetch_chart_data(ticker)
    
    pe = fundamentals.get("pe_ratio", "N/A")
    eps = fundamentals.get("eps", "N/A")
    price = fundamentals.get("price", 0.0)
    
    logs.append(f"Fetched {fundamentals.get('name')}. Price: ${price}, P/E: {pe}, EPS: {eps}")
    
    return {
        "fundamentals": fundamentals,
        "market_data": market_data,
        "logs": logs,
        "current_step": "fetch_data"
    }
