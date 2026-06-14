import json
import logging
from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage
from stock_predictor.agent.state import AgentState
from stock_predictor.services.sentiment import analyze_text_sentiment
from stock_predictor.agent.nodes.base import get_llm

logger = logging.getLogger(__name__)

def generate_fallback_bearish_thesis(ticker: str, fundamentals: Dict[str, Any], press_release: str, bullish_thesis: str) -> str:
    """
    Generates a highly realistic, fundamentals-driven bearish thesis challenging the bull.
    """
    name = fundamentals.get("name", ticker)
    pe = fundamentals.get("pe_ratio")
    eps = fundamentals.get("eps", 0.0)
    sentiment = analyze_text_sentiment(press_release)
    
    p1 = f"**Bearish Counter-Thesis for {ticker} ({name}):**\n"
    p1 += "The bullish advocate's perspective overlooks critical micro and macro risks. "
    
    if pe is not None:
        if pe > 25:
            p1 += f"Specifically, a P/E multiple of **{pe}** is heavily bloated. The stock is priced for perfection, leaving zero margin for error. If the company fails to maintain explosive double-digit growth, a sharp multiple contraction is inevitable."
        else:
            p1 += f"Although the trailing P/E is apparently low at **{pe}**, this is a classic value trap. Low multiples often reflect declining market share, shrinking margins, or structural industry decline that will suppress future EPS (currently at **${eps:.2f}**)."
    else:
        p1 += f"The absence of standard PE multiples indicates earnings instability or negative cash flows, which introduces considerable speculative risk for retail investors."

    p2 = ""
    if sentiment["label"] == "BULLISH":
        p2 = f"Furthermore, the bullish analyst is overly optimistic about the recent press announcement. In reality, statements regarding new initiatives are largely public relations exercises. Translating these announcements into actual bottom-line net income will take quarters, if not years, and involves massive execution risks."
    else:
        p2 = f"The downbeat news sentiment confirms that the company is facing stiff headwinds. Supply chain bottlenecks, inflation, and growing competitor pressure are eroding its core business, and management has not shown a clear roadmap to reverse this trend."
        
    p3 = f"To summarize, buying {ticker} at these levels ignores valuation realities and key execution risks. We recommend a cautious stance, as macro headwinds are likely to drag the stock price down in the coming months."
    
    return f"{p1}\n\n{p2}\n\n{p3}"

def bearish_analyst_node(state: AgentState) -> Dict[str, Any]:
    ticker = state["ticker"]
    fundamentals = state["fundamentals"]
    press_release = state["press_release"]
    bullish_thesis = state["bullish_thesis"]
    iteration = state.get("iteration", 0)
    logs = state.get("logs", [])
    
    logs.append(f"Bearish Analyst (Challenger) is reviewing the bullish case (Iteration {iteration + 1})...")
    
    llm = get_llm()
    if llm:
        # LLM Mode
        prompt = f"""You are a Senior Bearish Equity Research Analyst (the Challenger). 
Your job is to challenge the bullish case for {ticker} ({fundamentals.get('name')}) and highlight all the key risks and reasons why the stock might be overvalued or face headwinds.

Stock Fundamentals:
{json.dumps(fundamentals, indent=2)}

User Provided News/Press Release:
\"\"\"{press_release}\"\"\"

Bullish Case proposed by your colleague:
\"\"\"{bullish_thesis}\"\"\"

Instructions:
1. Explicitly challenge the assumptions in the bullish thesis.
2. Analyze fundamental risks:
   - Comment on the P/E ratio: if it's high, argue the stock is priced for perfection and highly vulnerable. If it's low, argue it's a value trap due to structural issues.
   - Point out debt levels, sector headwinds, competitor advancements, or operational bottlenecks.
3. Critically analyze the user-provided news/press release (e.g., is it just marketing hype? Will it actually improve the bottom line?).
4. If you feel the bullish argument is completely overwhelming and you cannot justify a bearish stance, or if you agree on the main points, conclude your analysis exactly with the phrase "CONSENSUS: TRUE". Otherwise, conclude with "CONSENSUS: FALSE".
5. Be professional, critical, and objective. Format your response in 2-3 clean markdown paragraphs.
"""
        try:
            response = llm.invoke([
                SystemMessage(content="You are a Wall Street bearish equity research analyst and risk manager."),
                HumanMessage(content=prompt)
            ])
            bearish_thesis = response.content
        except Exception as e:
            logger.error(f"Error invoking LLM in bearish analyst: {e}")
            bearish_thesis = generate_fallback_bearish_thesis(ticker, fundamentals, press_release, bullish_thesis)
    else:
        # Fallback Mode
        bearish_thesis = generate_fallback_bearish_thesis(ticker, fundamentals, press_release, bullish_thesis)
        
    logs.append("Bearish Analyst completed counter-thesis construction.")
    
    consensus = False
    if "CONSENSUS: TRUE" in bearish_thesis.upper():
        consensus = True
        logs.append("Consensus reached during debate.")
        
    return {
        "bearish_thesis": bearish_thesis,
        "logs": logs,
        "current_step": "bearish_analyst",
        "iteration": iteration + 1,
        "consensus": consensus
    }
