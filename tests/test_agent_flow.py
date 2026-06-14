import pytest
from stock_predictor.agent.nodes import fetch_data_node
from stock_predictor.agent.graph import create_agent_graph
from mock_data_fetcher import fetch_fundamentals_mock, fetch_chart_data_mock

def test_fetch_data_node_success(monkeypatch):
    # Monkeypatch the fetcher imported in the agent nodes namespace
    monkeypatch.setattr("stock_predictor.agent.nodes.fetch_data.fetch_fundamentals", fetch_fundamentals_mock)
    monkeypatch.setattr("stock_predictor.agent.nodes.fetch_data.fetch_chart_data", fetch_chart_data_mock)
    
    initial_state = {
        "ticker": "AAPL",
        "logs": [],
        "current_step": "init"
    }
    
    result = fetch_data_node(initial_state)
    
    assert "fundamentals" in result
    assert "market_data" in result
    assert result["fundamentals"]["ticker"] == "AAPL"
    assert len(result["market_data"]) == 30
    assert result["current_step"] == "fetch_data"

def test_fetch_data_node_failure(monkeypatch):
    # Patch the fetcher in the nodes namespace to raise ValueError
    monkeypatch.setattr("stock_predictor.agent.nodes.fetch_data.fetch_fundamentals", fetch_fundamentals_mock)
    monkeypatch.setattr("stock_predictor.agent.nodes.fetch_data.fetch_chart_data", fetch_chart_data_mock)
    
    initial_state = {
        "ticker": "INVALID",
        "logs": [],
        "current_step": "init"
    }
    
    with pytest.raises(ValueError):
        fetch_data_node(initial_state)

@pytest.mark.asyncio
async def test_full_graph_execution(monkeypatch):
    # Monkeypatch the fetcher in the nodes namespace
    monkeypatch.setattr("stock_predictor.agent.nodes.fetch_data.fetch_fundamentals", fetch_fundamentals_mock)
    monkeypatch.setattr("stock_predictor.agent.nodes.fetch_data.fetch_chart_data", fetch_chart_data_mock)
    
    # Clear LLM API keys to force rules-based fallback mode
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    
    graph = create_agent_graph()
    
    initial_state = {
        "ticker": "AAPL",
        "press_release": "Apple announces revolutionary new AI chips with 50% power savings.",
        "logs": ["Starting"],
        "current_step": "init",
        "fundamentals": {},
        "market_data": [],
        "bullish_thesis": "",
        "bearish_thesis": "",
        "synthesis_report": "",
        "prediction": {}
    }
    
    final_state = await graph.ainvoke(initial_state)
    
    assert final_state["current_step"] == "moderator"
    assert final_state["fundamentals"]["ticker"] == "AAPL"
    assert final_state["bullish_thesis"] != ""
    assert final_state["bearish_thesis"] != ""
    assert final_state["synthesis_report"] != ""
    assert "direction" in final_state["prediction"]
    assert "rating" in final_state["prediction"]
