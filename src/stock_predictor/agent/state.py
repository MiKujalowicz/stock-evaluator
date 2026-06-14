from typing import Dict, Any, List, TypedDict

class AgentState(TypedDict, total=False):
    """
    State representing the current execution context of the stock prediction panel.
    """
    ticker: str
    press_release: str
    fundamentals: Dict[str, Any]
    market_data: List[Dict[str, Any]]
    bullish_thesis: str
    bearish_thesis: str
    synthesis_report: str
    prediction: Dict[str, Any]
    logs: List[str]
    current_step: str
    iteration: int
    consensus: bool
