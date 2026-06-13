from langgraph.graph import StateGraph, END
from stock_predictor.agent.state import AgentState
from stock_predictor.agent.nodes import (
    fetch_data_node,
    bullish_analyst_node,
    bearish_analyst_node,
    moderator_node
)

def create_agent_graph():
    """
    Creates and compiles the multi-agent prediction graph.
    Flow: fetch_data -> bullish_analyst -> bearish_analyst -> moderator -> END
    """
    # Initialize the graph with the defined state schema
    workflow = StateGraph(AgentState)
    
    # Register the debate nodes
    workflow.add_node("fetch_data", fetch_data_node)
    workflow.add_node("bullish_analyst", bullish_analyst_node)
    workflow.add_node("bearish_analyst", bearish_analyst_node)
    workflow.add_node("moderator", moderator_node)
    
    # Set the starting node
    workflow.set_entry_point("fetch_data")
    
    # Set standard sequential transitions
    workflow.add_edge("fetch_data", "bullish_analyst")
    workflow.add_edge("bullish_analyst", "bearish_analyst")
    workflow.add_edge("bearish_analyst", "moderator")
    
    # End state transition
    workflow.add_edge("moderator", END)
    
    # Compile the graph
    app = workflow.compile()
    return app
