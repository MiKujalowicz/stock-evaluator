import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from stock_predictor.services.data_fetcher import fetch_fundamentals, fetch_chart_data

def test_fetch_fundamentals_success():
    mock_info = {
        "longName": "Test Company Inc.",
        "currentPrice": 150.0,
        "marketCap": 500000000,
        "trailingPE": 25.5,
        "forwardPE": 20.2,
        "trailingEps": 5.88,
        "pegRatio": 1.2,
        "fiftyTwoWeekHigh": 180.0,
        "fiftyTwoWeekLow": 110.0,
        "sector": "Technology",
        "industry": "Software",
        "longBusinessSummary": "This is a test company summary."
    }
    
    with patch("yfinance.Ticker") as mock_ticker_class:
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.info = mock_info
        mock_ticker_class.return_value = mock_ticker_instance
        
        result = fetch_fundamentals("TEST")
        
        assert result["ticker"] == "TEST"
        assert result["name"] == "Test Company Inc."
        assert result["price"] == 150.0
        assert result["market_cap"] == 500000000
        assert result["pe_ratio"] == 25.5
        assert result["forward_pe"] == 20.2
        assert result["eps"] == 5.88
        assert result["peg_ratio"] == 1.2
        assert result["fifty_two_week_high"] == 180.0
        assert result["fifty_two_week_low"] == 110.0
        assert result["sector"] == "Technology"
        assert result["industry"] == "Software"
        assert result["summary"] == "This is a test company summary."

def test_fetch_fundamentals_empty_info():
    with patch("yfinance.Ticker") as mock_ticker_class:
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.info = {}
        mock_ticker_class.return_value = mock_ticker_instance
        
        with pytest.raises(ValueError, match="No info returned for ticker TEST"):
            fetch_fundamentals("TEST")

def test_fetch_fundamentals_missing_price_keys():
    # Has some keys but no currentPrice or regularMarketPrice
    mock_info = {
        "longName": "Test Company Inc.",
        "marketCap": 500000000,
    }
    with patch("yfinance.Ticker") as mock_ticker_class:
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.info = mock_info
        mock_ticker_class.return_value = mock_ticker_instance
        
        with pytest.raises(ValueError, match="No info returned for ticker TEST"):
            fetch_fundamentals("TEST")

def test_fetch_fundamentals_exception_propagation():
    with patch("yfinance.Ticker") as mock_ticker_class:
        mock_ticker_class.side_effect = ConnectionError("Failed to connect to API")
        
        with pytest.raises(ConnectionError, match="Failed to connect to API"):
            fetch_fundamentals("TEST")

def test_fetch_chart_data_success():
    # Mocking pandas DataFrame returned by stock.history
    dates = pd.date_range(start="2026-05-01", periods=3)
    mock_df = pd.DataFrame({
        "Close": [150.5, 151.2, 149.8]
    }, index=dates)
    
    with patch("yfinance.Ticker") as mock_ticker_class:
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.history.return_value = mock_df
        mock_ticker_class.return_value = mock_ticker_instance
        
        result = fetch_chart_data("TEST")
        
        assert len(result) == 3
        assert result[0] == {"date": "2026-05-01", "close": 150.5}
        assert result[1] == {"date": "2026-05-02", "close": 151.2}
        assert result[2] == {"date": "2026-05-03", "close": 149.8}

def test_fetch_chart_data_empty():
    with patch("yfinance.Ticker") as mock_ticker_class:
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.history.return_value = pd.DataFrame()
        mock_ticker_class.return_value = mock_ticker_instance
        
        with pytest.raises(ValueError, match="No history returned for TEST"):
            fetch_chart_data("TEST")

def test_fetch_chart_data_exception_propagation():
    with patch("yfinance.Ticker") as mock_ticker_class:
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.history.side_effect = RuntimeError("Service Unavailable")
        mock_ticker_class.return_value = mock_ticker_instance
        
        with pytest.raises(RuntimeError, match="Service Unavailable"):
            fetch_chart_data("TEST")
