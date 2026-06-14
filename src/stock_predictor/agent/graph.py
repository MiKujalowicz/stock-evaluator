from langgraph.graph import StateGraph, END
from stock_predictor.agent.state import AgentState
from stock_predictor.agent.nodes import (
    fetch_data_node,
    bullish_analyst_node,
    bearish_analyst_node,
    moderator_node
)

def should_continue_debate(state: AgentState):
    """
    Condition to stop the debate when consensus is reached 
    or when number of iterations is >= 5.
    """
    iteration = state.get("iteration", 0)
    consensus = state.get("consensus", False)
    
    if consensus or iteration >= 5:
        return "moderator"
    return "bullish_analyst"

def create_agent_graph():
    """
    Creates and compiles the multi-agent prediction graph.
    Flow: fetch_data -> bullish_analyst -> bearish_analyst <-> bullish_analyst
    Debate ends after consensus or >= 5 iterations -> moderator -> END
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
    
    # Add conditional edge from bearish_analyst based on iteration count and consensus
    workflow.add_conditional_edges(
        "bearish_analyst",
        should_continue_debate,
        {
            "moderator": "moderator",
            "bullish_analyst": "bullish_analyst"
        }
    )
    
    # End state transition
    workflow.add_edge("moderator", END)
    
    # Compile the graph
    app = workflow.compile()
    return app
